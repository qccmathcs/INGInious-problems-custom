# -*- coding: utf-8 -*-
#
# This file is part of INGInious. See the LICENSE and the COPYRIGHTS files for
# more information about the licensing of this file.

import os
import web
import json
import re
import sys
import gettext
from abc import ABCMeta, abstractmethod

from inginious.common.base import id_checker
from inginious.common.tasks_problems import BasicProblem
from inginious.frontend.task_problems import DisplayableBasicProblem
from inginious.frontend.parsable_text import ParsableText

__version__ = "0.1.dev0"

PATH_TO_PLUGIN = os.path.abspath(os.path.dirname(__file__))


class StaticMockPage(object):
    # TODO: Replace by shared static middleware and let webserver serve the files
    def GET(self, path):
        if not os.path.abspath(PATH_TO_PLUGIN) in os.path.abspath(os.path.join(PATH_TO_PLUGIN, path)):
            raise web.notfound()

        try:
            with open(os.path.join(PATH_TO_PLUGIN, "static", path), 'rb') as file:
                return file.read()
        except:
            raise web.notfound()

    def POST(self, path):
        return self.GET(path)


class CustomProblem(BasicProblem):
    """Basic problem with code input. Do all the job with the backend"""

    def __init__(self, task, problemid, content, translations=None):
        BasicProblem.__init__(self, task, problemid, content, translations)
        self._boxes = []
        self._box_types = {"input-text": InputBox, "input-decimal": InputBox, "input-integer": InputBox,
                           "multiline": MultilineBox, "text": TextBox, "file": FileBox}
        if task.get_environment() is None:
            raise Exception("Environment undefined, but there is a problem with type=code or type=code-single-line")

        self._init_boxes(content)

    def get_boxes(self):
        """ Returns all the boxes of this code problem """
        return self._boxes

    @classmethod
    def get_type(cls):
        return "custom2"

    def input_is_consistent(self, task_input, default_allowed_extension, default_max_size):
        for box in self._boxes:
            if not box.input_is_consistent(task_input, default_allowed_extension, default_max_size):
                return False
        return True

    def input_type(self):
        return str

    def _init_boxes(self, content):
        if "boxes" in content:
            self._boxes = []
            for boxid, box_content in content['boxes'].items():
                if boxid == "":
                    raise Exception("Empty box ids are not allowed")
                self._boxes.append(self._create_box(boxid, box_content))

    def _create_box(self, boxid, box_content):
        """ Create adequate box """
        if not id_checker(boxid) and not boxid == "":
            raise Exception("Invalid box _id " + boxid)
        if "type" not in box_content:
            raise Exception("Box " + boxid + " does not have a type")
        if box_content["type"] not in self._box_types:
            raise Exception("Unknown box type " + box_content["type"] + " for box _id " + boxid)

        return self._box_types[box_content["type"]](self, boxid, box_content)

    def check_answer(self, _, __):
        return None, None, None, 0

    @classmethod
    def parse_problem(self, problem_content):
        return BasicProblem.parse_problem(problem_content)

    @classmethod
    def get_text_fields(cls):
        return BasicProblem.get_text_fields()



class DisplayableCustomProblem(CustomProblem, DisplayableBasicProblem):
    """ A displayable match problem """

    def __init__(self, task, problemid, content, translations=None):
        CustomProblem.__init__(self, task, problemid, content, translations)
        self._box_types = {
            "input-text": DisplayableInputBox,
            "input-decimal": DisplayableInputBox,
            "input-integer": DisplayableInputBox,
            "multiline": DisplayableMultilineBox,
            "text": DisplayableTextBox,
            "file": DisplayableFileBox}
        self._init_boxes(content)

    @classmethod
    def get_type_name(cls, gettext):
        return "custom 2"

    def adapt_input_for_backend(self, input_data):
        for box in self._boxes:
            input_data = box.adapt_input_for_backend(input_data)
        return input_data

    def show_input(self, template_helper, language, seed):
        """ Show BasicCodeProblem and derivatives """
        output = ""
        for box in self._boxes:
            output += box.show(template_helper, language)
        return output

    @classmethod
    def get_renderer(cls, template_helper):
        """ Get the renderer for this class problem """
        return template_helper.get_custom_renderer(os.path.join(PATH_TO_PLUGIN, "templates"), False)

    @classmethod
    def show_editbox(cls, template_helper, key):
        return DisplayableCustomProblem.get_renderer(template_helper).custom_edit(key)


class BasicBox(object, metaclass=ABCMeta):
    """ A basic abstract problem box. A box is a small input for a problem. A problem can contain multiple boxes """

    @abstractmethod
    def get_type(self):
        """ Return the type of this box """
        return None

    def get_problem(self):
        """ Return the problem to which this box is linked """
        return self._problem

    def get_id(self):
        """ Return the _id of this box """
        return self._id

    def input_is_consistent(self, task_input, default_allowed_extension, default_max_size):  # pylint: disable=unused-argument
        """ Check if an input for this box is consistent. Return true if this is case, false else """
        try:
            return self.get_complete_id() in task_input
        except:
            return False

    def get_complete_id(self):
        """ Returns the complete _id of this box. This _id is unique among all problems and boxes in an exercice """
        pid = str(self.get_problem().get_id())
        bid = str(self.get_id())
        if bid != "":
            return pid + "/" + bid
        else:
            return pid

    def __init__(self, problem, boxid, boxdata_):
        """ Constructor. problem is a BasicProblem (or derivated) instance, boxid a an alphanumeric _id and boxdata is the data for this box. """
        if not id_checker(boxid) and not boxid == "":
            raise Exception("Invalid box _id: " + boxid)
        self._id = boxid
        self._problem = problem

    @classmethod
    def get_renderer(cls, template_helper):
        """ Get the renderer for this class problem """
        return template_helper.get_custom_renderer(os.path.join(PATH_TO_PLUGIN, "templates"), False)


class TextBox(BasicBox):
    """Text box. Simply shows text."""

    def get_type(self):
        return "text"

    def input_is_consistent(self, task_input, default_allowed_extension, default_max_size):
        # do not call input_is_consistent from BasicBox.
        return True

    def __init__(self, problem, boxid, boxData):
        super(TextBox, self).__init__(problem, boxid, boxData)
        if "content" not in boxData:
            raise Exception("Box _id " + boxid + " with type=text do not have content.")
        self._content = boxData['content']


class FileBox(BasicBox):
    """
        File box. Allow to send a file to the inginious.backend.
        The input for this box must be a dictionnary, containing two keys:
        ::

            {
                "filename": "thefilename.txt",
                "value": "the content of the file"
            }

    """

    def get_type(self):
        return "file"

    def input_is_consistent(self, taskInput, default_allowed_extension, default_max_size):
        if not BasicBox.input_is_consistent(self, taskInput, default_allowed_extension, default_max_size):
            return False

        try:
            if not taskInput[self.get_complete_id()]["filename"].endswith(tuple(self._allowed_exts or default_allowed_extension)):
                return False

            if sys.getsizeof(taskInput[self.get_complete_id()]["value"]) > (self._max_size or default_max_size):
                return False
        except:
            return False
        return True

    def __init__(self, problem, boxid, boxData):
        super(FileBox, self).__init__(problem, boxid, boxData)
        self._allowed_exts = boxData.get("allowed_exts", None)
        self._max_size = boxData.get("max_size", None)


class InputBox(BasicBox):
    """ Input box. Displays an input object """

    def get_type(self):
        return "input"

    def input_is_consistent(self, taskInput, default_allowed_extension, default_max_size):
        if not BasicBox.input_is_consistent(self, taskInput, default_allowed_extension, default_max_size):
            return False

        if self._max_chars != 0 and len(taskInput[self.get_complete_id()]) > self._max_chars:
            return False

        # do not allow empty answers
        try:
            if len(taskInput[self.get_complete_id()]) == 0:
                if self._optional:
                    taskInput[self.get_complete_id()] = self._default_value
                else:
                    return False
        except:
            return False

        if self._input_type == "integer":
            try:
                int(taskInput[self.get_complete_id()])
            except:
                return False

        if self._input_type == "decimal":
            try:
                float(taskInput[self.get_complete_id()])
            except:
                return False
        return True

    def __init__(self, problem, boxid, boxData):
        super(InputBox, self).__init__(problem, boxid, boxData)
        if boxData["type"] == "input-text":
            self._input_type = "text"
            self._default_value = ""
        elif boxData["type"] == "input-integer":
            self._input_type = "integer"
            self._default_value = "0"
        elif boxData["type"] == "input-decimal":
            self._input_type = "decimal"
            self._default_value = "0.0"
        else:
            raise Exception("No such box type " + boxData["type"] + " in box " + boxid)

        self._optional = boxData.get("optional", False)

        if "maxChars" in boxData and isinstance(boxData['maxChars'], int) and boxData['maxChars'] > 0:
            self._max_chars = boxData['maxChars']
        elif "maxChars" in boxData:
            raise Exception("Invalid maxChars value in box " + boxid)
        else:
            self._max_chars = 0


class MultilineBox(BasicBox):
    """ Multiline Box """

    def get_type(self):
        return "multiline"

    def input_is_consistent(self, taskInput, default_allowed_extension, default_max_size):
        if not BasicBox.input_is_consistent(self, taskInput, default_allowed_extension, default_max_size):
            return False
        if self._max_chars != 0 and len(taskInput[self.get_complete_id()]) > self._max_chars:
            return False
        # do not allow empty answers
        if len(taskInput[self.get_complete_id()]) == 0:
            if self._optional:
                taskInput[self.get_complete_id()] = ""
            else:
                return False
        return True

    def __init__(self, problem, boxid, boxData):
        super(MultilineBox, self).__init__(problem, boxid, boxData)
        if "maxChars" in boxData and isinstance(boxData['maxChars'], int) and boxData['maxChars'] > 0:
            self._max_chars = boxData['maxChars']
        elif "maxChars" in boxData:
            raise Exception("Invalid maxChars value in box " + boxid)
        else:
            self._max_chars = 0

        self._optional = boxData.get("optional", False)

        if "lines" in boxData and isinstance(boxData['lines'], int) and boxData['lines'] > 0:
            self._lines = boxData['lines']
        elif "lines" in boxData:
            raise Exception("Invalid lines value in box " + boxid)
        else:
            self._lines = 8

        if re.match(r'[a-z0-9\-_\.]+$', boxData.get("language", ""), re.IGNORECASE):
            self._language = boxData.get("language", "")
        elif boxData.get("language", ""):
            raise Exception("Invalid language " + boxData["language"])
        else:
            self._language = "plain"


class DisplayableBox(object, metaclass=ABCMeta):
    """ A basic interface for displayable boxes """

    def __init__(self, problem, boxid, boxData):
        pass

    def adapt_input_for_backend(self, input_data):
        """ Adapt the input from web.py for the inginious.backend """
        return input_data

    @abstractmethod
    def show(self, renderer, language):
        """ Get the html to show this box """
        pass

    @classmethod
    def get_renderer(cls, template_helper):
        """ Get the renderer for this class problem """
        return template_helper.get_renderer(False)


class DisplayableTextBox(TextBox, DisplayableBox):
    """ A displayable text box """

    def __init__(self, problem, boxid, boxData):
        super(DisplayableTextBox, self).__init__(problem, boxid, boxData)

    def show(self, template_helper, language):
        """ Show TextBox """
        return str(DisplayableTextBox.get_renderer(template_helper).box_text(ParsableText(self._content, "rst", translation=gettext.NullTranslations())))


class DisplayableFileBox(FileBox, DisplayableBox):
    """ A displayable file box """

    def __init__(self, problem, boxid, boxData):
        super(DisplayableFileBox, self).__init__(problem, boxid, boxData)

    def adapt_input_for_backend(self, input_data):
        try:
            input_data[self.get_complete_id()] = {"filename": input_data[self.get_complete_id()].filename,
                                                  "value": input_data[self.get_complete_id()].value}
        except:
            input_data[self.get_complete_id()] = {}
        return input_data

    def show(self, template_helper, language):
        """ Show FileBox """
        return str(DisplayableFileBox.get_renderer(template_helper).box_file(self.get_complete_id(), self._max_size, self._allowed_exts, json))


class DisplayableInputBox(InputBox, DisplayableBox):
    """ A displayable input box """

    def __init__(self, problem, boxid, boxData):
        super(DisplayableInputBox, self).__init__(problem, boxid, boxData)

    def show(self, template_helper, language):
        """ Show InputBox """
        return str(DisplayableInputBox.get_renderer(template_helper).box_input(self.get_complete_id(), self._input_type, self._max_chars, self._optional))


class DisplayableMultilineBox(MultilineBox, DisplayableBox):
    """ A displayable multiline box """

    def __init__(self, problem, boxid, boxData):
        super(DisplayableMultilineBox, self).__init__(problem, boxid, boxData)

    def show(self, template_helper, language):
        """ Show MultilineBox """
        return str(DisplayableMultilineBox.get_renderer(template_helper).box_multiline(self.get_complete_id(), self._lines, self._max_chars, self._language, self._optional))


def init(plugin_manager, course_factory, client, plugin_config):
    # TODO: Replace by shared static middleware and let webserver serve the files
    plugin_manager.add_page('/plugins/demo/static/(.+)', StaticMockPage)
    plugin_manager.add_hook("css", lambda: "/plugins/demo/static/custom.css")
    plugin_manager.add_hook("javascript_header", lambda: "/plugins/demo/static/custom.js")
    course_factory.get_task_factory().add_problem_type(DisplayableCustomProblem)
