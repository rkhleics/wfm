wfm
===

Logging into the WorkflowMax UI to put times in sucks, so you put it off. If
you could enter times at the command line, where you already were, you might
actually stay on top of things.

Setup and use
-------------

You're going to need to get API keys from WorkflowMax. Believe it or not, you
do this by `emailing them`_. They tend to respond reasonably soon. Once you've
got your API keys, make a file at ``~/.wfm.yml`` containing something to the
effect of:

::
   
   email: me@company.tld
   apiKey: 00000000000000000000000000000000
   accountKey: 00000000000000000000000000000000

That should be you all set up. Assuming you've got pip installed (your package
manager probably has it if you don't, perhaps as ``python-pip``), you should be
able to run:

::
   
   $ pip install wfm
   $ wfm

Then follow the instructions the script gives you.

.. _emailing them: http://www.workflowmax.com/contact-us