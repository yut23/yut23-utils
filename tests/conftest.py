# SPDX-FileCopyrightText: 2024-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause

from hypothesis import Verbosity, settings

settings.register_profile("ci", max_examples=1000)
settings.register_profile("dev", max_examples=10)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
