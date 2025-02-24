import helpers.hasyncio as hasynci
import helpers.hobject as hobject
import helpers.hunit_test as hunitest
import oms.db.oms_db as odbomdb
import oms.portfolio.portfolio_example as opopoexa
import oms.test.oms_db_helper as omtodh

# #############################################################################
# Test_Portfolio_builders1
# #############################################################################


class Test_Portfolio_builders1(hunitest.TestCase):
    def test1(self) -> None:
        event_loop = None
        portfolio = opopoexa.get_DataFramePortfolio_example1(event_loop)
        # Check.
        hobject.test_object_signature(self, portfolio)


# #############################################################################
# Test_Portfolio_builders2
# #############################################################################


class Test_Portfolio_builders2(omtodh.TestOmsDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    def test1(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            table_name = odbomdb.CURRENT_POSITIONS_TABLE_NAME
            # Create DatabasePortfolio with some initial cash.
            portfolio = opopoexa.get_DatabasePortfolio_example1(
                event_loop,
                self.connection,
                table_name,
                asset_ids=[101],
            )
            # Check.
            hobject.test_object_signature(self, portfolio)
