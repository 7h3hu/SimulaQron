import os
import unittest
from argparse import ArgumentParser
from simulaqron.toolbox.manage_nodes import setup_cqc_files
import logging


logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)


def main(test_type="quick"):

    # First make sure CQC is set up
    setup_cqc_files()

    path_to_here = os.path.dirname(os.path.abspath(__file__))
    if test_type == "quick":
        directory = os.path.join(path_to_here, "tests", "auto", "quick")
    elif test_type == "full":
        directory = os.path.join(path_to_here, "tests", "auto")
    elif test_type == "network":
        directory = os.path.join(path_to_here, "tests", "auto", "quick", "network")
    else:
        raise ValueError("Unknown test type {}".format(test_type))

    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner()
    test_suite = test_loader.discover(start_dir=directory)
    result = test_runner.run(test_suite)

    return len(result.errors) == 0 and len(result.failures) == 0


def parse_args():
    parser = ArgumentParser()

    parser.add_argument('--quick', default=False, action='store_true')
    parser.add_argument('--full', default=False, action='store_true')

    args = parser.parse_args()
    if args.full:
        return "full"
    else:
        return "quick"


if __name__ == '__main__':
    test_type = parse_args()
    main()
