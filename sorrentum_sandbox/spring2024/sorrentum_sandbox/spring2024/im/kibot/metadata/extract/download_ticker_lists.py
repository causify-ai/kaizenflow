#!/usr/bin/env python

"""
# Download all ticker lists and push them to S3.

> download_ticker_lists.py

Import as:

import im.kibot.metadata.extract.download_ticker_lists as imkmedtili
"""
import logging
import os
import urllib.parse as uparse
from typing import List

import bs4
import requests

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hs3 as hs3
import helpers.hsystem as hsystem
import im.kibot.base.command as imkibacom
import im.kibot.data.extract.download as imkdaexdo
import im.kibot.metadata.config as imkimecon

_LOG = logging.getLogger(__name__)


# TODO(amr): reuse requests setup from extract/vkdedo.py.


def _extract_file_url_from_historical_page(page_url: str) -> str:
    """
    Extract txt file url from historical page.

    Example historical page url:
    http://www.kibot.com/Historical_Data/Top_50_Stocks_Historical_Intraday_Data.aspx.

    :return: file url, from example: http://www.kibot.com/Files/2/Top_50_Stocks_Intraday.txt
    """
    response = requests.get(url=page_url)
    page_soup = bs4.BeautifulSoup(response.content, "html.parser")
    file_link = page_soup.select('p a[href^="../Files"]')[0].attrs["href"]
    return uparse.urljoin(page_url, file_link)


def _extract_ticker_page_urls() -> List[str]:
    """
    Extract ticker page links from http://www.kibot.com/buy.aspx.

    :return: list of ticker page links, for example:
        ['http://www.kibot.com/Historical_Data/Top_50_Stocks_Historical_Intraday_Data.aspx', ...]
    """
    response = requests.get(url=imkimecon.ENDPOINT + "buy.aspx")
    soup = bs4.BeautifulSoup(response.content, "html.parser")

    available_data_sets = soup.select("strong a")
    return [imkimecon.ENDPOINT + s.attrs["href"] for s in available_data_sets]


# #############################################################################


class DownloadTickerListsCommand(imkibacom.KibotCommand):
    def __init__(self) -> None:
        super().__init__(docstring=__doc__, supports_tmp_dir=True)

    def customize_run(self) -> int:
        page_urls = _extract_ticker_page_urls()
        _LOG.info("Found %s historical page urls", len(page_urls))

        # TODO(amr): reuse parallelization logic in extract/vkdedo.py.

        for url in page_urls:
            _LOG.info("Processing historical page: %s", url)
            file_url = _extract_file_url_from_historical_page(page_url=url)
            _LOG.info("Extracted file url: %s", file_url)
            # TODO(amr): is cleaning the file name necessary? if so, let's move this function
            # to a more common place.
            file_name = os.path.basename(uparse.urlparse(file_url).path)
            # TODO(amr): is cleaning the file name necessary? if so, let's move this
            # function to a more common place.
            file_name = imkdaexdo.DatasetListExtractor._clean_dataset_name(  # pylint: disable=protected-access
                file_name
            )
            _LOG.info("Cleaned up file name: %s", file_name)

            # Download file.
            response = requests.get(file_url)
            hdbg.dassert_eq(response.status_code, 200)
            file_path = os.path.join(
                self.args.tmp_dir, imkimecon.TICKER_LISTS_SUB_DIR, file_name
            )
            hio.to_file(file_name=file_path, lines=str(response.content, "utf-8"))
            _LOG.info("Downloaded file to: %s", file_path)

            # Save to S3.
            aws_path = os.path.join(
                imkimecon.S3_PREFIX, imkimecon.TICKER_LISTS_SUB_DIR, file_name
            )
            hs3.dassert_is_s3_path(aws_path)

            # TODO(amr): create hs3.copy() helper.
            cmd = "aws s3 cp %s %s" % (file_path, aws_path)
            hsystem.system(cmd)
            _LOG.info("Uploaded file to s3: %s", aws_path)

        return 0


if __name__ == "__main__":
    DownloadTickerListsCommand().run()
