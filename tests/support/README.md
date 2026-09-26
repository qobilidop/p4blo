# Shared test support

Reusable program builders, catalogs, packet constructors and expected-answer
functions live here. Keep independent answers independent of the implementation
they check. A helper used by one test module can stay in that module; extract it
when another suite needs it. This directory contains no collected tests and
imports no test modules.
