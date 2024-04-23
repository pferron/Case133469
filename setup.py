# -*- coding: utf-8 -*-
"""This script is a setuptools/pip installer with hooks for running tests
(using pytest), inspecting code quality (pylint), and code formatting (black).

.. code-block:: console

    $ python setup.py test
    $ python setup.py lint
    $ python setup.py black
"""
from setuptools import setup, find_packages
import os
import sys
import re
import subprocess
import distutils.cmd
import distutils.log

VERSION = "1.0.0"


class PylintBuildError(Exception):
    """Raise an error from the linter."""

    pass


class PylintCommand(distutils.cmd.Command):
    """Run Pylint in the current environment on the installing package."""

    description = "run Pylint on the python source files"
    user_options = [
        ("pylint-rcfile=", None, "path to Pylint config file"),
        ("pylint-minimum-score=", None, "the minimum allowable score for passing builds"),
    ]

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        self.pylint_rcfile = "pylintrc"
        self.pylint_minimum_score = "10"

    def finalize_options(self):
        """Post-process options."""
        if self.pylint_rcfile:
            assert os.path.exists(self.pylint_rcfile), (
                "Pylint config file %s does not exist." % self.pylint_rcfile
            )
        if self.pylint_minimum_score:
            assert 0. <= float(self.pylint_minimum_score) <= 10., (
                "A score of %s is impossible" % self.pylint_minimum_score
            )

    def run(self):
        """Run Pylint on the distribution source directory."""

        # we want to source Pylint from the current environment so that we
        # don't get no-member version errors
        env_python = sys.executable.rsplit(os.path.sep, 1)[0]
        pylint = os.path.join(env_python, "pylint")

        curr_pkg = self.distribution
        top_level_pkgs = (
            package for package in curr_pkg.packages or curr_pkg.py_modules if "." not in package
        )
        for package in top_level_pkgs:

            command = [pylint, package]
            command += ["--rcfile={}".format(self.pylint_rcfile)]
            self.announce("Running command: %s" % str(command), level=distutils.log.INFO)

            pid = subprocess.Popen(command, stdout=subprocess.PIPE)
            out_bytes, _ = pid.communicate()
            out = out_bytes.decode("latin-1")

            if pid.returncode != 0:
                for line in out.splitlines():
                    self.announce(line, level=distutils.log.INFO)

                is_fatal = lambda status: status & 1
                is_error = lambda status: status & 2
                is_warning = lambda status: status & 4
                is_refactor = lambda status: status & 8
                is_convention = lambda status: status & 16

                if is_fatal(pid.returncode):
                    raise PylintBuildError("Fatal lint message")
                if is_error(pid.returncode):
                    raise PylintBuildError("Error lint message")
                if pid.returncode > 0:
                    raise PylintBuildError("Linting failure")

                textscore = re.search(r"Your code has been rated at ([0-9.]*)/10\W", out)
                score = float(textscore.group(1))
                if score < float(self.pylint_minimum_score):
                    raise PylintBuildError("Insufficient lint score: {}".format(score))
                self.announce("Pylint score: %s" % str(score), level=distutils.log.INFO)
            else:
                # Pylint has found no messages, so this is summary information
                for line in out.splitlines():
                    self.announce(line, level=distutils.log.DEBUG)


class BlackError(Exception):
    """Raise an error if the code is not black."""

    pass


class BlackCommand(distutils.cmd.Command):
    """Run black --check on the current environment on the installing
    package."""

    description = "run black on the python source files"
    user_options = [
        (
            "black-line-length=",
            None,
            "override the default line length that black allows when reformatting",
        )
    ]

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        self.black_line_length = "100"

    def finalize_options(self):
        """Post-process options."""
        pass

    def run(self):
        """Run Black on the distribution source directory."""

        # we want to source Pylint from the current environment so that we
        # don't get no-member version errors
        env_python = sys.executable.rsplit(os.path.sep, 1)[0]
        black = os.path.join(env_python, "black")

        curr_pkg = self.distribution
        top_level_pkgs = (
            package for package in curr_pkg.packages or curr_pkg.py_modules if "." not in package
        )
        for package in top_level_pkgs:
            command = [black, package]
            command += ["--line-length", "{}".format(self.black_line_length)]
            command += ["--check"]
            self.announce("Running command: %s" % str(command), level=distutils.log.INFO)

            pid = subprocess.Popen(command, stdout=subprocess.PIPE)
            out_bytes, _ = pid.communicate()
            out = out_bytes.decode("latin-1")

            if pid.returncode != 0:
                raise BlackError("Code is not black!")


if __name__ == "__main__":
    setup(
        name="rates-etl",
        cmdclass={"pylint": PylintCommand, "black": BlackCommand},
        version=VERSION,
        description="Rates ETL",
        author="CML Saturn",
        author_email="cml_top_gun@capitalone.com",
        url="https://github.kdc.capitalone.com/cml-pricing/rates-etl",
        packages=find_packages(),
        package_data={"": ["*.cfg", "*.csv", "*.csv.gz"]},
    )
