Pretix-easyVerein
==========================

This is a plugin for `pretix`_. 

Fetches and processes bankstatements from easyverein, transfers invoices to easyverein and syncs payment status.

What it does:

* [x] Trigger onlinebanking import with easyverein
* [x] Fetch bankstatement from easyverein and processes them in pretix
* [ ] Upload invoices (as well as cancelation invoices) to easyverein
* [ ] Mark invoice payed on eV and pretix if payment was detected
* [ ] Mark orders payed if invoice is marked payed on easyverein

Configuration:

* ev api key global or per organization
* ev non-api account global or per organization

Limitations:

* eV invoice status changes from payed to unpayed are not synced to pretix
* Cancelations of pretix invoices in eV are not synced to pretix

Periodic Task (every 6 hours):

1. (not-yet-implemented) Upload all not-yet-uploaded invoices to eV
2. Trigger eV bankstatement fetch
3. Get bookings (bankstatement) from eV for past 7 days
4. Process bankstatement
5. (not-yet-implemented) For all machted payments with associated invoice:
   1. If not already uploaded: upload invoice to eV
   2. Link booking and mark payed in eV
6. (not-yet-implemented) Check uploaded and unpaied invoices for payment in eV, mark payed

Manual Task (not-yet-implemented):

1. Get all invoices from eV
2. Identify invoices already present in eV, mark them as uploaded
3. Upload any not-yet-uploaded invoices to eV


Development setup
-----------------

1. Make sure that you have a working `pretix development setup`_.

2. Clone this repository.

3. Activate the virtual environment you use for pretix development.

4. Execute ``python setup.py develop`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.

This plugin has CI set up to enforce a few code style rules. To check locally, you need these packages installed::

    pip install flake8 isort black

To check your plugin for rule violations, run::

    black --check .
    isort -c .
    flake8 .

You can auto-fix some of these issues by running::

    isort .
    black .

To automatically check for these issues before you commit, you can run ``.install-hooks``.


License
-------


Copyright 2025 Julian Hammer

Released under the terms of the Apache License 2.0



.. _pretix: https://github.com/pretix/pretix
.. _pretix development setup: https://docs.pretix.eu/en/latest/development/setup.html
