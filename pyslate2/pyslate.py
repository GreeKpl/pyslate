from pyslate2.config import PyslateConfig
from pyslate2.locales import LOCALES
from pyslate2.parser import InnerTag, Placeholder, Variants
import numbers

class Pyslate:

    def __init__(self, language, backend=None, config=PyslateConfig()):
        self.config = config

        self.language = language
        self.backend = backend if backend else self.config.BACKEND_CLASS()
        self.cache = config.CACHE_CLASS() if self.config.ALLOW_CACHE else None
        self.fallbacks = {}
        self.global_fallback = config.GLOBAL_FALLBACK_LANGUAGE
        self.functions = {}
        self.parser = config.PARSER_CLASS()
        self.tags_grammar = {} # todo

    def translate(self, tag_name, **kwargs):
        return self._translate(tag_name, **kwargs)[0]

    def _translate(self, tag_name, **kwargs):
        if "number" in kwargs and not (self.config.DISABLE_NUMBER_FOR_VARIANT_TAGS and "#" in tag_name):
            languages = self._get_languages() + [self.config.NUMBER_FALLBACK_LANGUAGE]
            fallback = self._first_left_value(LOCALES, languages)["number_rule"](kwargs["number"])
            tag_name = tag_name.partition("#")[0] + "#" + fallback

        tag_base = tag_name.partition("#")[0]
        variant = tag_name.partition("#")[2]
        kwargs["tag_v"] = variant

        if tag_base in self.functions:
            helper = PyslateHelper(self)
            t9n = self.functions[tag_base](helper, tag_name, kwargs)
            grammar = helper.returned_grammar
        else:
            t9n, grammar = self._get_raw_content(tag_name), self._get_raw_grammar(tag_name)

        nodes = self.parser.parse(t9n)
        print(nodes)
        t9n = "".join([self.traverse(node, kwargs) for node in nodes])

        return t9n, grammar

    def _first_left_value(self, dictionary, keys):
        for key in keys:
            if key in dictionary:
                return dictionary[key]
        return None

    def localize(self, value):
        if not self.config.LOCALE_FORMAT_NUMBERS:
            return str(value)
        if isinstance(value, float):
            locale_data = self._first_left_value(LOCALES, [self.language, self.config.NUMBER_FALLBACK_LANGUAGE])
            return self._format_float(value, locale_data["format"]["decimal_point"])
        if isinstance(value, numbers.Integral):
            return str(value)
        else: # TODO date and time should be formatted too
            return str(value)

    def _format_float(self, n, decimal_point):
        formatted_float = "{:.3f}".format(n).rstrip("0").rstrip(".")
        if decimal_point != ".":
            formatted_float = formatted_float.replace(".", decimal_point)
        return formatted_float

    t = translate
    l = localize


    def set_fallback_language(self, base_language, fallback_language):
        self.fallbacks[base_language] = fallback_language

    def set_global_fallback(self, fallback_language):
        self.global_fallback = fallback_language

    def _get_languages(self):
        languages = [self.language]
        if self.language in self.fallbacks:
            languages += [self.fallbacks[self.language]]
        languages += [self.global_fallback]
        return languages

    def register_function(self, tag_name, function):
        self.functions[tag_name] = function

    def _get_raw_content(self, tag_name):
        """Gets and returns content from backend considering all possible tag and language fallbacks"""

        requested_tags = [tag_name]
        if "#" in tag_name:
            requested_tags += [tag_name.partition("#")[0]]

        retrieved_content = self.backend.get_content(requested_tags, self._get_languages())
        if retrieved_content is None:
            retrieved_content = "[MISSING TAG '{0}']".format(requested_tags[0])
        elif self.config.ALLOW_CACHE:
            self.cache.save(tag_name, self.language, retrieved_content)
        return retrieved_content

    def _get_raw_grammar(self, tag_name):
        """Gets and returns grammar from backend considering all possible tag and language fallbacks
        Returns none if no grammar is set"""
        requested_tags = [tag_name]
        if "#" in tag_name:
            requested_tags += [tag_name.partition("#")[0]]

        languages = self._get_languages()
        return self.backend.get_grammar(requested_tags, languages)

    def traverse(self, node, kwargs):
        if type(node) is InnerTag:
            tag_name = "".join([self.traverse(child, kwargs) for child in node.contents])
            if not self.config.ALLOW_INNER_TAGS:  # when inner tags are disabled then print them as-is
                return "${" + tag_name + "}"
            final_kwargs = kwargs

            if node.tag_id:
                if "groups" in kwargs:
                    final_kwargs = dict(kwargs)
                    del final_kwargs["groups"]
                    final_kwargs.update(kwargs["groups"][node.tag_id])

            text, grammar = self._translate(tag_name, **final_kwargs)
            if node.tag_id:
                self.tags_grammar[node.tag_id] = grammar
            return text
        elif type(node) is Placeholder:
            return self._replace_placeholder(node, kwargs)
        elif type(node) is Variants:
            if not self.config.ALLOW_VARIANTS_STRUCTURE:
                return ""
            return self._replace_variants(node, kwargs)
        elif type(node) is str:
            return node

    def _replace_placeholder(self, node, kwargs):
        if node.contents in kwargs:
            value = kwargs[node.contents]
            if isinstance(value, float):
                value = self.localize(value)
            return str(value)
        return "[MISSING VALUE FOR '{0}']".format(node.contents)

    def _replace_variants(self, node, kwargs):
        param_name = "variant"
        if node.tag_id:
            param_name = node.tag_id


        print("ZAPAMIETANE: ", self.tags_grammar)
        if param_name in kwargs and kwargs[param_name] in node.variants:
            return node.variants[kwargs[param_name]]
        elif param_name in self.tags_grammar and self.tags_grammar[param_name] in node.variants:
            return node.variants[self.tags_grammar[param_name]]
        else:
            return node.variants[node.first_key]


class PyslateHelper:

    def __init__(self, pyslate):
        self.pyslate = pyslate
        self.returned_grammar = None

    def translation(self, tag_name):
        self.pyslate._get_raw_content(tag_name)

    def translation_and_grammar(self, tag_name):
        return self.translation(tag_name), self.grammar(tag_name)

    def grammar(self, tag_name):
        return self.pyslate._get_raw_grammar(tag_name)

    def return_grammar(self, grammar):
        self.returned_grammar = grammar



