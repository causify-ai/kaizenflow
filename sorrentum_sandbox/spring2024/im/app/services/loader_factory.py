"""
Import as:

import im.app.services.loader_factory as imaselofa
"""
from typing import Any

import im.common.data.load.abstract_data_loader as imcdladalo

# TODO(*): Move it out to app/


class LoaderFactory:
    """
    Builds AbstractDataLoader objects based on different criteria (e.g.,
    provider and storage type).
    """

    @classmethod
    def get_loader(
        cls, storage_type: str, provider: str, **kwargs: Any
    ) -> imcdladalo.AbstractDataLoader:
        """
        Return a data loader for the requested `storage_type` and `provider`.

        :param storage_type: load from where (e.g., s3, sql)
        :param provider: provider (e.g., kibot, ib)
        :param kwargs: additional parameters for loader instantiation
        :raises ValueError: `storage_type` loader is not implemented for provider
        """
        if storage_type == "sql":
            loader = cls._get_sql_loader(provider, **kwargs)
        elif storage_type == "s3":
            loader = cls._get_s3_loader(provider)
        else:
            raise ValueError("Storage type %s is not supported" % storage_type)
        return loader

    @staticmethod
    def _get_s3_loader(provider: str) -> imcdladalo.AbstractS3DataLoader:
        """
        Return a data loader from S3 for the requested `provider`.

        :param provider: provider (e.g., kibot)
        :raises ValueError: if loader is not implemented for provider
        """
        loader: imcdladalo.AbstractS3DataLoader
        if provider == "kibot":
            import im.kibot.data.load.kibot_s3_data_loader as imkdlksdlo

            loader = imkdlksdlo.KibotS3DataLoader()
        elif provider == "ib":
            import im.ib.data.load.ib_s3_data_loader as imidlisdlo

            loader = imidlisdlo.IbS3DataLoader()
        else:
            raise ValueError("S3 loader for %s is not implemented" % provider)
        return loader

    @staticmethod
    def _get_sql_loader(
        provider: str, dbname: str, user: str, password: str, host: str, port: int
    ) -> imcdladalo.AbstractSqlDataLoader:
        """
        Return a data loader from SQL for the requested `provider`.

        :param provider: provider (e.g., kibot)
        :param dbname: database name to connect
        :param user: authorization user
        :param password: authorization password
        :param host: database host
        :param port: database port
        :raises ValueError: if SQL loader is not implemented for provider
        """
        loader: imcdladalo.AbstractSqlDataLoader
        if provider == "kibot":
            import im.kibot.data.load.kibot_sql_data_loader as ikdlksdlo

            loader = ikdlksdlo.KibotSqlDataLoader(
                dbname=dbname, user=user, password=password, host=host, port=port
            )
        elif provider == "ib":
            import im.ib.data.load.ib_sql_data_loader as iidlisdlo

            loader = iidlisdlo.IbSqlDataLoader(
                dbname=dbname, user=user, password=password, host=host, port=port
            )
        else:
            raise ValueError("SQL loader for %s is not implemented" % provider)
        return loader
