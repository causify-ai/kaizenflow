"""
Import as:

import im.ib.data.load.ib_sql_data_loader as iidlisdlo
"""
import helpers.hdbg as hdbg
import im.common.data.load.abstract_data_loader as imcdladalo
import im.common.data.types as imcodatyp


class IbSqlDataLoader(imcdladalo.AbstractSqlDataLoader):
    @staticmethod
    def _get_table_name_by_frequency(frequency: imcodatyp.Frequency) -> str:
        """
        Get table name by predefined frequency.

        :param frequency: a predefined frequency
        :return: table name in DB
        """
        table_name = ""
        if frequency == imcodatyp.Frequency.Minutely:
            table_name = "IbMinuteData"
        elif frequency == imcodatyp.Frequency.Daily:
            table_name = "IbDailyData"
        elif frequency == imcodatyp.Frequency.Tick:
            table_name = "IbTickData"
        hdbg.dassert(table_name, f"Unknown frequency {frequency}")
        return table_name
