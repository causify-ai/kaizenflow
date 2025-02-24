import helpers.hunit_test as hunitest
import helpers.lib_tasks_integrate as hlitaint


class Test_infer_dst_dir1(hunitest.TestCase):
    def test1(self) -> None:
        # Define input variables.
        src_dir = "/src/cmamp1/oms/broker/broker.py"
        # Call function to test.
        act = hlitaint._infer_dst_file_path(src_dir,
            default_src_dir_basename="cmamp1",
            default_dst_dir_basename="amp1",
            check_exists=False)
        # Define expected output.
        exp = (
            "/src/amp1/oms/broker/broker.py",
            "oms/broker/broker.py",
        )
        # Compare actual and expected output.
        self.assertEqual(act, exp)
