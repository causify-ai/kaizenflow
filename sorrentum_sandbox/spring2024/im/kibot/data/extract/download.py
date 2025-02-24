#!/usr/bin/env python
"""
Download data from kibot.com, compress each file, upload it to S3.

# Process only specific dataset:
> download.py --dataset all_stocks_1min --dry_run -u XYZ -p ABC

# Process only specific dataset:
> download.py --dataset all_stocks_1min

# Process several datasets:
> download.py --dataset all_stocks_1min --dataset all_stocks_daily

# Start from scratch and process all datasets:
> download.py --delete_s3_dir

# Debug
> download.py --serial -v DEBUG

Import as:

import im.kibot.data.extract.download as imkdaexdo
"""

import argparse
import logging
import os
import re
import shutil
import urllib.parse as uparse

import bs4
import joblib
import numpy as np
import pandas as pd
import requests
import requests.adapters as radapt
import requests.packages.urllib3.util as rpuuti  # pylint: disable=import-error
import tqdm

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hs3 as hs3
import helpers.hsystem as hsystem
import im.kibot.base.command as imkibacom
import im.kibot.data.config as imkidacon

_LOG = logging.getLogger(__name__)

_JOBLIB_NUM_CPUS = 10
_JOBLIB_VERBOSITY = 1

# #############################################################################


def _log_in(
    page_url: str,
    username: str,
    password: str,
    requests_session: requests.Session,
) -> bool:
    """
    Make a login request to the account page and return the result.

    :param page_url: URL to the account page
    :param username: username
    :param password: password
    :param requests_session: current requests session to preserve cookies
    :return: boolean for operation result
    """
    _LOG.debug("Requesting page '%s'", page_url)
    page_response = requests_session.get(page_url)
    page_content = str(page_response.content, "utf-8")
    soup = bs4.BeautifulSoup(page_content, "html.parser")
    view_state_input = soup.find("input", attrs={"name": "__VIEWSTATE"})
    event_validation_input = soup.find(
        "input", attrs={"name": "__EVENTVALIDATION"}
    )
    data = {
        "__VIEWSTATE": view_state_input.attrs.get("value"),
        "__EVENTVALIDATION": event_validation_input.attrs.get("value"),
        "ctl00$Content$LoginView1$Login1$UserName": username,
        "ctl00$Content$LoginView1$Login1$Password": password,
        "ctl00$Content$LoginView1$Login1$RememberMe": "on",
        "ctl00$Content$LoginView1$Login1$LoginButton": "  Log In  ",
    }
    _LOG.debug("Sending login request to page '%s'", page_url)
    _LOG.debug("Request data is %s", data)
    login_response = requests_session.post(
        page_url, data=data, allow_redirects=False
    )
    if login_response.status_code == 302:
        return True
    _LOG.error("Unexpected response from the login request")
    return False


def _download_page(
    page_file_path: str,
    page_url: str,
    requests_session: requests.Session,
) -> str:
    """
    Download html file by URL and store under specific name in data directory.

    :param page_file_path: path of the file
    :param page_url: URL from where to download
    :param requests_session: current requests session to preserve cookies
    :return: contents of the page
    """
    resolved_url = uparse.urljoin(imkidacon.ENDPOINT, page_url)
    _LOG.info("Requesting page '%s'", resolved_url)
    page_response = requests_session.get(resolved_url)
    _LOG.info("Storing page to '%s'", page_file_path)
    with open(page_file_path, "w+b") as f:
        f.write(page_response.content)
    page_content = str(page_response.content, "utf-8")
    return page_content


# #############################################################################


class DatasetListExtractor:
    """
    Extract the list of available datasets from Kibot.
    """

    @classmethod
    def extract_dataset_links(cls, src_file: str) -> pd.DataFrame:
        """
        Retrieve a table with datasets and corresponding page links.

        :param src_file: html file with the account page
        :return: DataFrame with dataset names and corresponding page links
        """
        html = hio.from_file(src_file)
        soup = bs4.BeautifulSoup(html, "html.parser")
        # Get last table.
        table = soup.findAll("table")[-1]
        df = pd.read_html(str(table))[0]
        df.columns = ["dataset", "link"]
        cols = [
            np.where(dataset.has_attr("href"), dataset.get("href"), "no link")
            for dataset in table.find_all("a")
        ]
        # Reset first column with links.
        df.link = [str(c) for c in cols]
        # Clean up dataset names for future ease reference.
        df.dataset = df.dataset.apply(cls._clean_dataset_name)
        return df

    @staticmethod
    def _clean_dataset_name(dataset: str) -> str:
        """
        Clean up a dataset name for ease future reference.

        E.g., the dataset `1. All Stocks 1min on 9/29/2019` becomes `all_stocks_1min`.

        :param dataset: input dataset name to process
        :return: cleaned dataset name
        """
        clean_dataset = dataset.lower()
        clean_dataset = re.sub(r"^\d+.", "", clean_dataset)
        clean_dataset = re.sub(r"\s+on.*$", "", clean_dataset)
        clean_dataset = re.sub(r"\s+", "_", clean_dataset)
        clean_dataset = re.sub(r"&", "", clean_dataset)
        clean_dataset = clean_dataset.strip("_")
        # TODO(amr): should we assert the result matches an element in `imkidacon.DATASETS`?
        return clean_dataset


# #############################################################################


class DatasetExtractor:
    """
    Extract payloads for a particular dataset.
    """

    def __init__(
        self, dataset: str, requests_session: requests.Session, aws_profile: str
    ):
        """
        Init object.

        :param dataset: input dataset name to process
        :param requests_session: current requests session to preserve cookies
        """
        self.dataset = dataset
        self.requests_session = requests_session
        self.aws_dir = os.path.join(imkidacon.get_s3_prefix(aws_profile), dataset)
        _LOG.info("Saving to S3 in '%s'", self.aws_dir)

    def delete_dataset_s3_directory(self) -> None:
        assert 0, "Very dangerous: are you sure?"
        _LOG.warning("Deleting s3 file %s", self.aws_dir)
        cmd = "aws s3 rm --recursive %s" % self.aws_dir
        hsystem.system(cmd)

    def download_payload_page(
        self,
        local_dir: str,
        row: pd.Series,
        download_compressed: bool,
        skip_if_exists: bool,
        clean_up_artifacts: bool,
    ) -> bool:
        """
        Store CSV payload for specific Symbol in S3.

        :param local_dir: local directory with the data
        :param row: series with Symbol and Link columns
        :param download_compressed: download gzipped already
        :param skip_if_exists: do not re-download
        :param clean_up_artifacts: remove files after download
        :return: boolean for operation result
        """
        aws_file = self.aws_dir + "/"
        aws_file += "%s.csv.gz" % row["Symbol"]
        s3fs = hs3.get_s3fs("am")
        # Check if S3 file exists.
        if skip_if_exists:
            exists = s3fs.exists(aws_file)
            if exists:
                _LOG.info("%s -> skip", aws_file)
                return False
        # Download data.
        local_file = "%s/%s.csv" % (local_dir, row["Symbol"])
        dst_file = local_file.replace(".csv", ".csv.gz")
        self._download_file(
            row["Link"], local_file, dst_file, download_compressed
        )
        # Copy to S3.
        hs3.dassert_is_s3_path(aws_file)
        cmd = "aws s3 cp %s %s" % (dst_file, aws_file)
        hsystem.system(cmd)
        #
        if clean_up_artifacts:
            # Delete local file.
            cmd = "rm -f %s" % dst_file
            hsystem.system(cmd)
        return True

    def get_dataset_payloads_to_download(
        self,
        dataset_links_df: pd.DataFrame,
        source_dir: str,
        converted_dir: str,
    ) -> pd.DataFrame:
        """
        Get a DataFrame with the list of Symbols and Links to download for a
        dataset.

        :param dataset_links_df: DataFrame with the list to a dataset pages
        :param source_dir: directory to store source download
        :param converted_dir: directory to store converted download
        :return: DataFrame with Symbol and Link columns
        """
        dataset_html_file = os.path.join(source_dir, f"{self.dataset}.html")
        dataset_csv_file = os.path.join(converted_dir, f"{self.dataset}.csv")
        # Download dataset html page.
        if not os.path.exists(dataset_html_file):
            _LOG.warning("Missing %s: downloading it", dataset_html_file)
            links = dataset_links_df.loc[
                dataset_links_df.dataset == self.dataset
            ].link.values
            if len(links) == 0:
                hdbg.dfatal(
                    "Can't find a link corresponding to the request dataset"
                )
            if len(links) != 1:
                hdbg.dfatal(
                    "Found multiple links corresponding to the requested dataset: %s"
                    % links
                )
            hdbg.dassert_eq(len(links), 1, "links=%s", links)
            link_to_html_page = links[0]
            _download_page(
                dataset_html_file, link_to_html_page, self.requests_session
            )
        # Parse and convert dataset's html page.
        _LOG.warning("Parsing '%s'", dataset_html_file)
        dataset_df = self._extract_payload_links(dataset_html_file)
        dataset_df.to_csv(dataset_csv_file)
        _LOG.info(
            "Number of files to download: %s:\n%s",
            dataset_df.shape[0],
            dataset_df.head(),
        )
        return dataset_df

    def store_dataset_csv_file(self, converted_dir: str) -> None:
        """
        Store dataset CSV file with Link and Symbol columns on S3.

        :param converted_dir: directory to store converted download
        """
        _LOG.debug("Storing %s dataset CSV file on S3", self.dataset)
        dataset_csv_file = os.path.join(converted_dir, f"{self.dataset}.csv")
        dataset_csv_s3_file = os.path.join(self.aws_dir, f"{self.dataset}.csv")
        # Copy to S3.
        hs3.dassert_is_s3_path(dataset_csv_s3_file)
        cmd = "aws s3 cp %s %s" % (dataset_csv_file, dataset_csv_s3_file)
        hsystem.system(cmd)

    @staticmethod
    def _extract_payload_links(src_file: str) -> pd.DataFrame:
        """
        Extract a table from dataset html page.

        :param src_file: path to dataset html file page
        :return: DataFrame with the list of series with Symbol and Link columns
        """
        html = hio.from_file(src_file)
        # Find HTML that refers a required table.
        _, table_start, rest = html.partition('<table class="ms-classic4-main">')
        table, table_end, _ = rest.partition("</table>")
        # Replace all anchors with their href attributes.
        table = re.sub('<a.*?href="(.*?)">(.*?)</a>', "\\1", table)
        # Construct back the table.
        table = table_start + table + table_end
        df = pd.read_html(table)[0]
        df.columns = df.iloc[0]
        df = df.iloc[1:]
        return df

    def _download_file(
        self, link: str, local_file: str, dst_file: str, download_compressed: bool
    ) -> None:
        """
        Download file from the link, store it as local_file and then gzip it as
        dst_file. Optionally, download it already gzipped.

        :param link: URL from where to download
        :param local_file: path to local .csv file
        :param dst_file: path to local .csv.gz file
        :param download_compressed: download gzipped already
        """
        headers = {"accept-encoding": "gzip"} if download_compressed else None
        with self.requests_session.get(link, headers=headers, stream=True) as r:
            with open(dst_file, "wb") as f:
                shutil.copyfileobj(r.raw, f)
        if not download_compressed:
            # Compress.
            cmd = "gzip %s -c >%s" % (local_file, dst_file)
            hsystem.system(cmd)
            # Delete csv file.
            cmd = "rm -f %s" % local_file
            hsystem.system(cmd)


# #############################################################################


class AdjustmentsDatasetExtractor(DatasetExtractor):
    """
    Extractor of payloads for an adjustments dataset.

    Is a child of DatasetExtractor since requires a separate handling.
    """

    def __init__(self, dataset: str, requests_session: requests.Session):
        super().__init__(dataset, requests_session)
        self.dataset = dataset
        self.requests_session = requests_session

    def get_adjustments_to_download(
        self,
        source_dir: str,
        converted_dir: str,
    ) -> pd.DataFrame:
        """
        Get a DataFrame with the list of Symbols and Links to download for a
        dataset.

        :param source_dir: directory to store source download
        :param converted_dir: directory to store converted download
        :return: DataFrame with Symbol and Link columns
        """
        dataset_txt_file = os.path.join(source_dir, f"{self.dataset}.txt")
        dataset_csv_file = os.path.join(converted_dir, f"{self.dataset}.csv")
        _LOG.debug("Making request to adjustments API")
        response = self.requests_session.get(
            imkidacon.API_ENDPOINT,
            params={"action": "adjustments", "symbolsonly": 1},
        )
        with open(dataset_txt_file, "w+b") as f:
            f.write(response.content)
        dataset_df = pd.read_csv(dataset_txt_file, header=None)
        dataset_df.drop_duplicates(inplace=True)
        dataset_df.columns = ["Symbol"]
        dataset_df["Link"] = dataset_df["Symbol"].apply(
            self._get_adjustments_payload_link
        )
        dataset_df.to_csv(dataset_csv_file)
        dataset_df.reset_index(drop=True, inplace=True)
        _LOG.info("Number of files to download: %s", dataset_df.shape[0])
        _LOG.info(dataset_df.head())
        return dataset_df

    def get_dataset_payloads_to_download(
        self, dataset_links_df: pd.DataFrame, source_dir: str, converted_dir: str
    ) -> pd.DataFrame:
        return self.get_adjustments_to_download(source_dir, converted_dir)

    @staticmethod
    def _get_adjustments_payload_link(symbol: str) -> str:
        """
        Get the link to download adjustment data for a symbol.

        :param symbol: symbol of the adjustment payload
        :return: a link to download
        """
        query_params = "?"
        query_params += uparse.urlencode(
            {"action": "adjustments", "symbol": symbol}
        )
        api_link = uparse.urljoin(imkidacon.API_ENDPOINT, query_params)
        return api_link  # type: ignore

    def _download_file(
        self, link: str, local_file: str, dst_file: str, download_compressed: bool
    ) -> None:
        super()._download_file(link, local_file, dst_file, download_compressed)
        csv_table = pd.read_table(dst_file, sep="\t")
        csv_table.to_csv(dst_file, index=False)


# #############################################################################


class DownloadDataCommand(imkibacom.KibotCommand):
    def __init__(self) -> None:
        super().__init__(
            docstring=__doc__, supports_tmp_dir=True, requires_auth=True
        )

    @staticmethod
    def customize_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--start_from",
            type=int,
            default=None,
            help="Define the index of the first payload to download",
        )
        parser.add_argument(
            "--dataset",
            type=str,
            help="Download a specific dataset (or all datasets if omitted)",
            choices=imkidacon.DATASETS,
            action="append",
            default=None,
        )
        parser.add_argument(
            "--serial", action="store_true", help="Download data serially"
        )
        parser.add_argument(
            "--dry_run", action="store_true", help="Just do a dry-run"
        )
        parser.add_argument(
            "--no_download_compressed",
            action="store_true",
            help="Do not download data compressed on server side",
        )
        parser.add_argument(
            "--no_skip_if_exists",
            action="store_true",
            help="Do not skip if it exists on S3",
        )
        parser.add_argument(
            "--no_clean_up_artifacts",
            action="store_true",
            help="Do not clean artifacts",
        )
        parser.add_argument(
            "--delete_s3_dir",
            action="store_true",
            help="Delete the S3 dir before starting uploading (dangerous)",
        )

    def customize_run(self) -> int:
        return _run(args=self.args)


def _run(args) -> int:  # type: ignore
    # TODO(amr): This is kept as a separate function to minimize the diff, should be
    # cleaned up at some point
    # Create dirs.
    incremental = not args.no_incremental
    source_dir_name = "source_data"
    source_dir = os.path.join(args.tmp_dir, source_dir_name)
    hio.create_dir(source_dir, incremental=incremental)
    #
    converted_dir_name = "converted_data"
    converted_dir = os.path.join(args.tmp_dir, converted_dir_name)
    hio.create_dir(converted_dir, incremental=incremental)
    # Log in.
    requests_session = requests.Session()
    requests_retry = rpuuti.Retry(
        total=12,
        backoff_factor=2,
        status_forcelist=[104, 403, 500, 501, 502, 503, 504],
    )
    requests_session.mount(
        "http://", radapt.HTTPAdapter(max_retries=requests_retry)
    )
    requests_session.mount(
        "https://", radapt.HTTPAdapter(max_retries=requests_retry)
    )
    kibot_account = imkidacon.ENDPOINT + "account.aspx"
    login_result = _log_in(
        kibot_account, args.username, str(args.password), requests_session
    )
    if not login_result:
        # Unable to login.
        return -1
    my_account_file = os.path.join(source_dir, "my_account.html")
    # Download my account html page.
    if not os.path.exists(my_account_file):
        _LOG.warning("Missing '%s': downloading it", my_account_file)
        _download_page(my_account_file, kibot_account, requests_session)
    # Parse and convert my account page.
    dataset_links_csv_file = os.path.join(converted_dir, "dataset_links.csv")
    _LOG.warning("Parsing %s", my_account_file)
    dle = DatasetListExtractor()
    dataset_links_df = dle.extract_dataset_links(
        os.path.join(source_dir, "my_account.html")
    )
    _LOG.info(
        "Found %d datasets to download:\n%s",
        len(dataset_links_df),
        dataset_links_df,
    )
    # Save the file.
    dataset_links_df.to_csv(dataset_links_csv_file)
    _LOG.info("Saved dataset list to download in '%s'", dataset_links_csv_file)
    # Process a dataset.
    datasets_to_proceed = args.dataset or imkidacon.DATASETS
    for dataset in tqdm.tqdm(datasets_to_proceed, desc="dataset"):
        # Create dataset dir.
        dataset_dir = os.path.join(converted_dir, dataset)
        hio.create_dir(dataset_dir, incremental=True)
        # Create payload extractor instance.
        if dataset == "adjustments":
            de: DatasetExtractor = AdjustmentsDatasetExtractor(
                dataset, requests_session
            )
        else:
            de = DatasetExtractor(dataset, requests_session)
        if args.delete_s3_dir:
            de.delete_dataset_s3_directory()
        to_download = de.get_dataset_payloads_to_download(
            dataset_links_df,
            source_dir,
            converted_dir,
        )
        de.store_dataset_csv_file(converted_dir)
        if not args.dry_run:
            if args.start_from:
                _LOG.warning(
                    "Starting from payload %d / %d as per user request",
                    args.start_from,
                    to_download.shape[0],
                )
                hdbg.dassert_lte(0, args.start_from)
                hdbg.dassert_lt(args.start_from, to_download.shape[0])
                to_download = to_download.iloc[args.start_from :]
            func = lambda row: de.download_payload_page(
                dataset_dir,
                row,
                **{
                    "download_compressed": not args.no_download_compressed,
                    "skip_if_exists": not args.no_skip_if_exists,
                    "clean_up_artifacts": not args.no_clean_up_artifacts,
                },
            )
            tqdm_ = tqdm.tqdm(
                to_download.iterrows(),
                total=len(to_download),
                desc="Downloading Kibot data",
            )
            # Run dataset downloads.
            if not args.serial:
                joblib.Parallel(
                    n_jobs=_JOBLIB_NUM_CPUS, verbose=_JOBLIB_VERBOSITY
                )(joblib.delayed(func)(row) for _, row in tqdm_)
            else:
                for _, row in tqdm_:
                    func(row)
        else:
            _LOG.warning("Skipping download as per user requested")
    return 0


if __name__ == "__main__":
    DownloadDataCommand().run()
