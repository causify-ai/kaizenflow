import helpers.hasyncio as hasynci
import helpers.hobject as hobject
import helpers.hunit_test as hunitest
import oms.broker.broker_example as obrbrexa
import oms.test.oms_db_helper as omtodh

# #############################################################################
# Test_Broker_builders1
# #############################################################################


class Test_Broker_builders1(hunitest.TestCase):
    def test1(self) -> None:
        event_loop = None
        broker = obrbrexa.get_DataFrameBroker_example1(event_loop)
        # Check.
        hobject.test_object_signature(self, broker)


# #############################################################################
# Test_Broker_builders2
# #############################################################################


class Test_Broker_builders2(omtodh.TestOmsDbHelper):
    @classmethod
    def get_id(cls) -> int:
        return hash(cls.__name__) % 10000

    def test1(self) -> None:
        with hasynci.solipsism_context() as event_loop:
            broker = obrbrexa.get_DatabaseBroker_example1(
                event_loop, self.connection
            )
            # Check.
            hobject.test_object_signature(self, broker)
