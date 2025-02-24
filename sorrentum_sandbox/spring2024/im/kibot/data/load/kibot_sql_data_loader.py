"""
Import as:

import im.kibot.data.load.kibot_sql_data_loader as imkdlksdlo
"""

import helpers.hdbg as hdbg
import im.common.data.load.abstract_data_loader as imcdladalo
import im.common.data.types as imcodatyp


class KibotSqlDataLoader(imcdladalo.AbstractSqlDataLoader):
    @staticmethod
    def _get_table_name_by_frequency(frequency: imcodatyp.Frequency) -> str:
        """
        Get table name by predefined frequency.

        :param frequency: a predefined frequency
        :return: table name in DB
        """
        table_name = ""
        if frequency == imcodatyp.Frequency.Minutely:
            table_name = "KibotMinuteData"
        elif frequency == imcodatyp.Frequency.Daily:
            table_name = "KibotDailyData"
        elif frequency == imcodatyp.Frequency.Tick:
            table_name = "KibotTickData"
        hdbg.dassert(table_name, f"Unknown frequency {frequency}")
        return table_name
