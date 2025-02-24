"""
Import as:

import oms.child_order_quantity_computer.child_order_quantity_computer_instances as ocoqccoqci
"""
import oms.child_order_quantity_computer.child_order_quantity_computer as ocoqccoqc
import oms.child_order_quantity_computer.dynamic_scheduling_child_order_quantity_computer as ocoqcdscoqc
import oms.child_order_quantity_computer.static_scheduling_child_order_quantity_computer as ocoqcsscoqc


def get_child_order_quantity_computer_instance1(
    scheduler_type: str,
) -> ocoqccoqc.AbstractChildOrderQuantityComputer:
    """
    Instantiate child order quantity computer object.

    :param scheduler_type: a type of scheduler to use
    :return: an instance of `AbstractChildOrderQuantityComputer` object
    """
    if scheduler_type == "StaticSchedulingChildOrderQuantityComputer":
        return ocoqcsscoqc.StaticSchedulingChildOrderQuantityComputer()
    elif scheduler_type == "DynamicSchedulingChildOrderQuantityComputer":
        return ocoqcdscoqc.DynamicSchedulingChildOrderQuantityComputer()
    else:
        raise ValueError("scheduler_type='%s' not supported" % scheduler_type)
