## Contributing to pycomm3

This document aims to provide a brief guide on how to contribute to `pycomm3`.  

### Who can contribute?

Anyone! Contributions from any user are welcome.  Contributions aren't limited to changing code. 
Filing bug reports, asking questions, adding examples or documentation are all ways to contribute.
New users may find it helpful to start with improving documentation, type hinting, or tests.  

## Asking a question

Questions can be submitted as either an issue or a discussion post.  A general question not directly related to the code
or one that may be beneficial to other users would be most appropriate in the discussions area.  One that is about a 
specific feature or could turn into a feature request or bug report would be more appropriate as an issue.  If submitting
a question as an issue, please use the _question_ template.  

## Submitting an Issue

No code is perfect, `pycomm3` is no different and user submitted issues aid in improving the quality of this library.
Before submitting an issue, check to see if someone has already submitted one before so we can avoid duplicate issues. 

### Bug Reports

To submit a bug report, please create an issue using the _Bug Report_ template. Please include as much information as 
possible relating to the bug.  The more detailed the bug report, the easier and faster it will be to resolve.
Some details to include:
- The version of `pycomm3` (easily found with the `pip show pycomm3` command)
- Model/Firmware/etc if the issue is related to a specific device or firmware version
- Logs (see the [documentation](https://pycomm3.dev/getting_started.html#logging) to configure)
  - A helper method is provided to simplify logging configs, including logging to a file  
  - Using the `LOG_VERBOSE` level is the most helpful
- Sample code that will reproduce the bug

### Feature Requests

For feature requests or enhancements, please create an issue using the _Feature Request_ template.  New features could be
things like:
- A missing feature from a similar library
    - e.g. Library _X_ has a feature _Y_, would it be possible to add _Y_ functionality to `pycomm3`?
- Change or modification to the API
    - If it's a breaking change be sure to include why the new functionality is better than the current
- Enhancing a current feature
- Removing an old/broken/unsupported feature


## Submitting Changes

Submitting code or documentation changes is another way to contribute.  All contributions should be made in the form of 
a pull request.  You should fork this repository and clone it to your machine.  All work is done in the `develop` branch 
first before merging to `master`.  All pull requests should target the `develop` branch.  This is because some of the 
tests are specific to a demo PLC.  Once changes are completed in `develop` and all tests are passing, `develop` will
be merged into `master` and a new release created and available on PyPI. 

Some requirements for code changes to be accepted include:

- code should be _pythonic_ and follow PEP8, PEP20, and other Python best-practices or common conventions
- public methods should have docstrings which will be included in the documentation
- comments and docstrings should explain _why_ and _how_ the code works, not merely _what_ it is doing
- type hinting should be used as much as possible, all public methods need to have hints
- new functionality should have tests
- run the _user_ tests and verify there are no issues
- avoid 3rd party dependencies, code should only require the Python standard library
- avoid breaking changes, unless adequately justified
- do not update the library version

Some suggested contributions include:
- type hinting
    - all public methods are type hinted, but many internal methods are missing them
- tests
    - new tests are always welcome, particularly offline tests or any methods missing tests
- examples
    - example scripts showing how to use this library or any of it's features
    - you may include just the example script if you're not comfortable with also updating the docs to include it
    

### New Feature or an Example?

It can be tough to decide whether functionality should be added to the library or shown as an example.  New features 
should apply to generally to almost all devices for a driver or implement new functionality that cannot be done externally.
If submitting an example, please include name/username/email/etc in a comment/docstring if you wish to be credited.

Here are a couple examples of changes and why they were added either as a feature or example:

**[Feature] Add support for writing structures with a dictionary for the value:**
- Cannot be done without modifying internal methods
- New functionality not yet implemented
- Improves user experience
    - user can read a struct, change one value, and write it back without changing the data structure

**[Example] Add support for reading/writing Powerflex drive parameters:**
- Implemented using the `generic_message` method
- Does not apply to a wide arrange of device types
- Not a PLC, so doesn't fit in the Logix or SLC drivers
- Too specific for the CIPDriver, but not enough to create a new driver

Some questions to ask yourself when deciding between a feature or an example:
- Is this new functionality or a new use of current functionality? _Former may be a feature, latter could be an example_
- Can this be done using already available features? _Yes, then maybe an example_
- Does this apply to a wide arrange of devices? _Yes, then maybe a feature_
- Will this require internal changes to existing functionality? _Yes, then maybe a feature_
- Is this useful? _Either should be useful_

