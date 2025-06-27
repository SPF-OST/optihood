import unittest as _ut
import subprocess as _sp


class TestGurobi(_ut.TestCase):
    def test_license_available(self):
        failure_texts = ["Error", "Fail", "expired"]
        results = _sp.run("gurobi_cl", capture_output=True, text=True)
        if any(ss in results.stdout for ss in failure_texts):
            raise AssertionError(f"\nLicense issue: \n{results.stdout}")


if __name__ == '__main__':
    _ut.main()
