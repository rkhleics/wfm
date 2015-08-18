wfm
===

Logging into the WorkflowMax UI to put times in sucks, so you put it off. If
you could enter times at the command line, where you already were, you might
actually stay on top of things.

Setup and use
-------------

You're going to need to get API keys from WorkflowMax. Believe it or not, you
do this by `emailing them`_. They tend to respond reasonably soon. If you have
a colleague who already has a set, just use theirs; we decide which user to
update as based on email address. Once you have your keys, make a file at
``~/.wfm.yml`` containing something to the effect of:

.. code-block:: yaml
   
   email: me@company.tld
   apiKey: 00000000000000000000000000000000
   accountKey: 00000000000000000000000000000000

That should be you all set up. Assuming you've got pip installed (your package
manager probably has it if you don't, perhaps as ``python-pip``, ``pip`` or
just as part of ``python``), you should be able to run ``pip install wfm``. If
it's a system Python install, it may be necessary to run `pip install` as root
with `sudo`.

Then, just run ``wfm`` and follow the instructions the script gives you.

.. _emailing them: http://www.workflowmax.com/contact-us
