Pyslate syntax reference
========================

Decorators
----------
Decorators are constructs applicable to tags or variable fields to modify their value.
They are python functions which take tag value string as input and return output string.
They are added after the end of tag key and are prefixed by “@”.
They are left-associative e.g. “**some_tag@article@capitalize**” means first adding an article, then capitalizing the first letter.

::

    {
        "buying_toy": {
            "en":  "I've bought ${toy_%{name}@article}."
        },
        "toy_rocking_horse": {
            "en": "rocking horse"
        },
        "toy_autosan": {
            "en": "autosan"
        }
    }

    >>> pyslate_en.t("buying_toy", name="rocking_horse")
    I've bought a rocking horse.
    >>> pyslate_en.t("buying_toy", name="autosan")
    I've bought an autosan.


Apart from built-in decorators it’s possible to define custom ones.

::

    {
        "some_message": {
            "en":  "Important message"
        },
        message_container": {
            "en":  "Message is: ${some_message@add_dots}"
        }
    }

    def add_dots(value):
        return ".".join(value)

    pyslate_en.register_decorator("add_dots", add_dots)

    >>> pyslate_en.t("message_container")
    Message is: I.m.p.o.r.t.a.n.t. .m.e.s.s.a.g.e

    >>> pyslate_en.t("message_container@add_dots")
    M.e.s.s.a.g.e. .i.s.:. .I...m...p...o...r...t...a...n...t... ...m...e...s...s...a...g...e


It's possible to decorate both requested tag, inner tag fields and variable fields.
In the last command, value of "some_message" tag gets dots added and then the whole texts gets dots added.
There are three dots between the letters, because second decorator adds dots between
every single character, including dots added by first decorator.

.. _Available_Decorators:

Available decorators
^^^^^^^^^^^^^^^^^^^^

By default Pyslate provides the following decorators in the default scope:

 - ``capitalize`` - make the first character have upper case and the rest lower case
 - ``upper`` - convert to uppercase
 - ``lower`` - convert to lowercase

For English an additional decorator is available:

 - ``article`` - add *a* or *an* article to a word. *an* is added if the first letter of the word is a vowel, *a* otherwise.


Custom functions
----------------
Custom functions allow you to do almost unlimited manipulation over the produced text.
They are kind of magic tag, which, when referenced, executes python code
to produce the correct tag value on-the-fly based on input arguments.

Every custom function needs to take 3 parameters:

 - ``helper`` - a class being a wrapper for Pyslate object that allows you to perform certain operations, instance of :py:class:`pyslate.PyslateHelper <pyslate.pyslate.PyslateHelper>`
 - ``name`` - full name of requested tag (including its variant)
 - ``params`` - dict of all parameters (names and values of variable fields) specified for the tag

::

    {
        "some_tag": {
            "en":  "%{person:m?He|f?She} is ${person:some_custom}."
        },
        "template_person": {
            "en": "%{firstname} %{lastname} (SSN: %{ssn})"
        }
    }

    def some_custom_function(helper, name, params):
        people_database = {
            9203139: {"firstname": "John", "lastname": "Johnson", "sex": "m"},
            9203312: {"firstname": "Judy", "lastname": "Brown", "sex": "f"},
            9493839: {"firstname": "Edward", "lastname": "Smith", "sex": "m"},
        }

        ssn_number = params["ssn"]
        person = people_database[ssn_number]

        helper.return_form(person["sex"])  # it's to make tag's grammar form available outside

        return helper.translation("template_person", firstname=person["firstname"], lastname=person["lastname"], ssn=ssn_number)

Let's register this function:

::

    >>> pyslate_en.register_function("some_custom", some_custom_function)
    >>> pyslate_en.t("some_tag", ssn=9203312)
    She is Judy Brown (SSN: 9203312).

A few things to notice: it's possible to set grammatical form for the text generated by a custom function.
It would look like "template_person" tag is unnecessary and it would be ok to replace the last line in the some_custom_function to:

::

    return "{} {} (SSN: {})".format(person["firstname"], person["lastname"], ssn_number)


It would work, but it's not a good idea. We want to make text fully internationalizable, while in some countries the opposite order of first and lastname is used.
It should be possible to format such texts for every language to look natural.
Translator usually doesn't have knowledge nor ability to change python code, so it's better to keep text format in a separate tag.


'params' argument contains a full dict of key-value pairs consisting of: explicit parameters, context parameters
and special parameters (e.g. *tag_v*), so they are all available in the function body.

Let's see it in another example, where func_print_all displays full name of called pseudo-tag and all its parameters:

::

    def func_print_all(helper, name, params):
        return name + " | " + str(params)

    >>> pyslate_en = Pyslate("en", backend=JsonBackend("translations.json"))
    >>> pyslate_en.register_function("print_all", func_print_all)
    >>> pyslate_en.context = {"name": "John", "age": 18}

    >>> pyslate_en.t("print_all#f", arg1=True, arg2="help me")
    "print_all#f | {'arg1': True, 'age': 18, 'tag_v': 'f', 'name': 'John', 'arg2': 'help me'}"

