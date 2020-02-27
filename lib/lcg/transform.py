# -*- coding: utf-8 -*-

# Copyright (C) 2012-2015 OUI Technology Ltd.
# Copyright (C) 2019-2020 Tomáš Cerha <t.cerha@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import unicode_literals
from future import standard_library
from builtins import chr
from builtins import range

import html.parser
import html.entities
import io
import re
import sys
import xml.dom.minidom
import xml.etree.ElementTree

import lcg

standard_library.install_aliases()
unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


class Processor(object):
    """Common markup language parser and tree structure transformer.

    It transformers a markup language input to anything else.  The
    transformation is performed by 'transform()' method.  You can customize the
    parsing and transformation process by subclassing this class and its inner
    classes.

    See inner classes 'Parser' and 'Transformer' for more information.

    """

    class Parser(object):
        """Markup language parser.

        It parses unicode input into 'xml.etree.ElementTree.Element' structure.
        The parser is invoked by calling 'lcg_parse()' method.

        In this class the parser does nothing; it must be subclassed and
        'lcg_parse()' redefined.

        """

        _TEXT_REPLACEMENTS = ((re.compile('</(?P<tag>em|strong)>( *)<(?P=tag)>'), '\\2',),
                              (re.compile('<(?P<tag>em|strong)>( *)</(?P=tag)>'), '\\2',),
                              )

        def _text_process(self, html):
            for regexp, replacement in self._TEXT_REPLACEMENTS:
                html = regexp.sub(replacement, html)
            return html

        def lcg_parse(self, data):
            """Parse 'data' and return 'xml.etree.ElementTree.Element' instance.

            Arguments:

              data -- markup language input; unicode

            In this class the method does nothing, you must redefine it in
            some subclass.

            """
            pass

    class Transformer(object):
        """'xml.etree.ElementTree.Element' tree transformer.

        Transformation is performed by calling 'transform()' method.

        The transformation process is primarily customized by redefining
        'Transformer._matchers' method which defines the transformation rules.
        The method returns sequence of pairs (MATCHER, HANDLER).  MATCHER is a
        tuple of the form (TAG-REGEXP, (ATTRIBUTE-NAME, ATTRIBUTE-REGEXP),
        ...).  TAG-REGEXP is a regular expression matching the whole tag name;
        ATTRIBUTE-REGEXP is a regular expression matching the whole value of
        attribute ATTRIBUTE-NAME, undefined attributes are handled as empty
        strings.  Alternatively MATCHER can be also a function of single
        argument, the element, returning True iff the element matches.  The
        first matching pair is used for transformation of each of the elements.
        It is an error if an element doesn't match any of the matchers -- such
        elements couldn't be transformed.

        HANDLER is a pair of the form (FUNCTION, KWARGS).  Function is a
        function of two non-optional arguments: The handled element and a
        sequence of the following elements (siblings) on the same level (this
        argument is useful when the content of the corresponding result element
        consists not only of the handled element but also from some elements
        following it, e.g. in case of HTML x LCG sections).  Dictionary of
        additional KWARGS to be passed to the called function may be provided.
        The handler function is responsible for processing element's
        subelements, typically 'Transformer.transform' method is applied on
        them and the returned instances are inserted into the transformed
        element.  Several typical handling functions (methods) are predefined
        in 'Transformer' subclasses.

        """

        def __init__(self):
            object.__init__(self)
            self._make_matchers()

        def _matchers(self):
            return ()

        def _make_matchers(self):
            matchers = self._matchers()
            compiled_matchers = []
            for test, handler in matchers:
                if isinstance(test, basestring):
                    test = (test,)
                if isinstance(test, (tuple, list)):
                    tag_regexp = re.compile(test[0] + '$')
                    attr_tests = [(a, re.compile(r),) for a, r in test[1:]]

                    def test_function(element, tag_regexp=tag_regexp, attr_tests=attr_tests):
                        if not tag_regexp.match(element.tag):
                            return False
                        for attr, regexp in attr_tests:
                            try:
                                value = element.attrib[attr]
                            except KeyError:
                                return False
                            if not regexp.match(value + '$'):
                                return False
                        return True
                elif callable(test):
                    test_function = test
                else:
                    raise Exception("Invalid matcher test specification", test)
                if not isinstance(handler, (tuple, list)):
                    handler = (handler, {})
                compiled_matchers.append((test_function, handler))
            self._compiled_matchers = compiled_matchers

        def _make_content(self, tag, attributes, children, text=None):
            """Make and return new 'xml.etree.ElementTree.Element'.

            Arguments:

              tag -- tag of the element; string
              attributes -- dictionary of attribute names (keys; strings) and
                attribute values (values; basestrings) of the newly created
                element
              childern -- sequence of 'xml.etree.ElementTree.Element' instances
                to be set as children of the newly created element.
              text -- if not 'None' then add the text (basestring) to the
                element.  Note this represents just the text immediately after
                the opening tag in XML serialization; it is often a good idea
                not to make elements combining both text and children (although
                there is nothing wrong if they do).

            """
            attr = {}
            for k, v in attributes.items():
                if v is not None:
                    attr[k] = v
            element = xml.etree.ElementTree.Element(tag, attr)
            for i in range(len(children)):
                element.insert(i, children[i])
            if text is not None:
                element.text = text
            return element

        def transform(self, element, _followers=None):
            """Transform 'element' and return the result.

            The method transforms the first element in 'element' (including
            'element' itself) that matches any of the matchers returned from
            '_matchers()' method.

            Arguments:

              element -- 'xml.etree.ElementTree.Element' instance

            The result may be arbitrary, it depends on particular 'Transformer'
            subclass.

            """
            if _followers is None:
                _followers = []
            for test, handler in self._compiled_matchers:
                if test(element):
                    function, kwargs = handler
                    return function(element, _followers, **kwargs)
            raise Exception("No transformation available for element", element)

    def transform(self, data):
        """Transform input 'data' and return the result.

        Arguments:

          data -- markup language input; unicode

        The result is dependent on particular 'Processor' class.

        """
        assert isinstance(data, basestring), data
        tree = self.Parser().lcg_parse(data)
        return self.Transformer().transform(tree)


class XMLProcessor(Processor):
    """Processor working on LCG XML input.

    TODO: LCG XML should be defined here.

    """

    class Parser(Processor.Parser):

        _TAG_PRESERVE_WHITESPACE = {'preformatted': True,
                                    'list': False,
                                    'definitions': False,
                                    'table': False,
                                    'row': False}

        def _lcg_dom_content(self, element):
            from xml.etree import ElementTree
            top = element
            tree = ElementTree.Element('_lcg')

            def subexport(tree, node):
                if hasattr(node, 'tagName'):
                    spacing = self._TAG_PRESERVE_WHITESPACE.get(node.tagName)
                else:
                    spacing = False
                child_nodes = node.childNodes
                last_node = tree
                final_node = child_nodes and child_nodes[-1]
                for n in child_nodes:
                    export(tree, n, last_node, final_node, spacing)
                    tree_children = list(tree)
                    if tree_children:
                        last_node = tree_children[-1]

            def export(parent_tree, node, preceding_node, final_node, spacing):
                node_type = node.nodeType
                if node_type == node.ELEMENT_NODE:
                    tree = ElementTree.SubElement(parent_tree, node.tagName)
                    attributes = node.attributes
                    for i in range(attributes.length):
                        a = attributes.item(i)
                        tree.set(a.name, a.value)
                    subexport(tree, node)
                elif node_type == node.TEXT_NODE or node_type == node.ENTITY_NODE:
                    value = node.nodeValue
                    if spacing is True:
                        if preceding_node is parent_tree and value and value[0] == '\n':
                            value = value[1:]
                        if node is final_node and value and value[-1] == '\n':
                            value = value[:-1]
                    elif spacing is False:
                        value = value.strip()
                    else:
                        if preceding_node is parent_tree:
                            value = value.lstrip()
                        if node is final_node:
                            value = value.rstrip()
                    if value:
                        if preceding_node is parent_tree:
                            assert not parent_tree.text, node
                            parent_tree.text = value
                        else:
                            assert not preceding_node.tail, preceding_node
                            preceding_node.tail = value
                elif node_type == node.COMMENT_NODE:
                    pass
                else:
                    raise Exception('Unhandled node type', node, node.nodeType)
            assert len(top.childNodes) == 1, top.childNodes
            subexport(tree, top)
            return list(tree)[0]

        def lcg_parse(self, xml_):
            import xml.dom.minidom
            xml_ = self._text_process(xml_.encode('utf-8'))
            dom = xml.dom.minidom.parseString(xml_)
            return self._lcg_dom_content(dom)

    class Transformer(Processor.Transformer):

        def _matchers(self):
            return ()

        def _transform_sub(self, element, children=None):
            """Transform 'element' children and return the result.

            Arguments:

              element -- element whose children should be transformed;
                'xml.etree.ElementTree.Element' instance
              children -- if 'None' then transform 'element' children,
                otherwise transform the given sequence of
                'xml.etree.ElementTree.Element' instances


            The return value is a sequence of transformed children, each of the
            values is as returned from 'transform()' method.

            """
            if children is None:
                children = list(element)
            return [self.transform(c) for c in children]


class XML2Content(XMLProcessor):
    """Processor transforming LCG XML to LCG 'Content'."""

    class Transformer(XMLProcessor.Transformer):

        def __init__(self):
            XMLProcessor.Transformer.__init__(self)
            self._in_table_heading = False

        def _matchers(self):
            return (
                ('container', (self._container, dict(class_=lcg.Container))),
                ('citation', (self._container, dict(class_=lcg.Citation))),
                ('strong', (self._container, dict(class_=lcg.Strong))),
                ('emphasized', (self._container, dict(class_=lcg.Emphasized))),
                ('underlined', (self._container, dict(class_=lcg.Underlined))),
                ('subscript', (self._container, dict(class_=lcg.Subscript))),
                ('superscript', (self._container, dict(class_=lcg.Superscript))),
                ('new-page', (self._single, dict(class_=lcg.NewPage))),
                ('new-line', (self._single, dict(class_=lcg.NewLine))),
                ('separator', (self._single, dict(class_=lcg.HorizontalSeparator))),
                ('text', self._text),
                ('preformatted', (self._text, dict(class_=lcg.PreformattedText))),
                ('mathml', (self._text, dict(class_=lcg.MathML))),
                (('paragraph', ('align', 'right')),
                 (self._container, dict(class_=lcg.Paragraph,
                                        halign=lcg.HorizontalAlignment.RIGHT))),
                (('paragraph', ('align', 'center')),
                 (self._container, dict(class_=lcg.Paragraph,
                                        halign=lcg.HorizontalAlignment.CENTER))),
                (('paragraph', ('align', 'justify')),
                 (self._container, dict(class_=lcg.Paragraph,
                                        halign=lcg.HorizontalAlignment.JUSTIFY))),
                ('paragraph', (self._container, dict(class_=lcg.Paragraph))),
                (('list', ('order', 'lower-alpha')),
                 (self._container, dict(class_=lcg.ItemizedList,
                                        order=lcg.ItemizedList.LOWER_ALPHA))),
                (('list', ('order', 'upper-alpha')),
                 (self._container, dict(class_=lcg.ItemizedList,
                                        order=lcg.ItemizedList.UPPER_ALPHA))),
                (('list', ('order', 'numeric')),
                 (self._container, dict(class_=lcg.ItemizedList, order=lcg.ItemizedList.NUMERIC))),
                ('list', (self._container, dict(class_=lcg.ItemizedList))),
                ('section', self._section),
                ('definitions', self._definitions),
                ('anchor', self._anchor),
                ('link', self._link),
                ('audio', (self._media, dict(class_=lcg.InlineAudio))),
                ('video', (self._media, dict(class_=lcg.InlineVideo))),
                ('image', self._image),
                ('table', self._table),
                ('row', (self._container, dict(class_=lcg.TableRow))),
                ('cell', self._table_cell),
            )

        def _transform_sub(self, element, children=None):
            if children is None:
                children = list(element)
            transformed = []

            def add_text(text):
                if text:
                    transformed.append(lcg.TextContent(text))
            add_text(element.text)
            for c in children:
                transformed.append(self.transform(c))
                add_text(c.tail)
            return transformed

        def _container(self, element, followers, class_=lcg.Container, **kwargs):
            return class_(self._transform_sub(element), **kwargs)

        def _single(self, element, followers, class_=lcg.Content, **kwargs):
            return class_(**kwargs)

        def _text(self, element, followers, class_=lcg.TextContent, **kwargs):
            return class_(element.text, **kwargs)

        def _section(self, element, followers):
            text_title = element.attrib.get('title', '')
            children = list(element)
            if children and children[0].tag == 'heading':
                heading_content = self._transform_sub(children[0])
                if len(heading_content) == 1:
                    heading = heading_content[0]
                else:
                    heading = lcg.Container(heading_content)
                children = children[1:]
            else:
                heading = None
            content = self._transform_sub(element, children)
            return lcg.Section(text_title, content, heading=heading)

        def _definitions(self, element, followers):
            paired_items = [self._transform_sub(e) for e in element]
            return lcg.DefinitionList(paired_items)

        def _anchor(self, element, followers):
            name = element.attrib['name']
            text = element.text
            return lcg.Anchor(anchor=name, text=text)

        def _link(self, element, followers):
            label = self._transform_sub(element)[0]
            target = element.attrib['target']
            return lcg.Link(target=target, label=label)

        def _media(self, element, followers, class_=None, **kwargs):
            return class_(element.attrib['target'], name=element.attrib['name'], **kwargs)

        def _image(self, element, followers):
            alignment = {'left': lcg.InlineImage.LEFT,
                         'right': lcg.InlineImage.RIGHT}.get(element.attrib.get('align'))
            return self._media(element, followers, class_=lcg.InlineImage, align=alignment)

        def _table(self, element, followers):
            return lcg.Table(self._transform_sub(element), title=element.attrib.get('title'))

        def _table_cell(self, element, followers):
            content = self._transform_sub(element)
            alignment = {'left': lcg.TableCell.LEFT,
                         'right': lcg.TableCell.RIGHT,
                         'center': lcg.TableCell.CENTER}.get(element.attrib.get('align'))
            class_ = lcg.TableHeading if element.attrib.get('heading') == '1' else lcg.TableCell
            return class_(content, align=alignment)


class XML2HTML(XMLProcessor):
    """Processor transforming LCG XML to editor HTML.

    This is just a base class, intended to be subclassed for each supported
    HTML editor.

    """

    class Transformer(XMLProcessor.Transformer):

        def _matchers(self):
            return (
                ('container', self._container),
                ('citation', (self._container, dict(tag='blockquote'))),
                ('strong', (self._container, dict(tag='strong'))),
                ('emphasized', (self._container, dict(tag='em'))),
                ('underlined', (self._container, dict(tag='u'))),
                ('subscript', (self._container, dict(tag='sub'))),
                ('superscript', (self._container, dict(tag='sup'))),
                ('new-page', (self._container, dict(tag='div', style='page-break-after: always;'))),
                ('new-line', (self._container, dict(tag='br'))),
                ('separator', (self._container, dict(tag='hr'))),
                ('text', self._text),
                ('preformatted', (self._container, dict(tag='pre'))),
                ('mathml', self._mathml),
                (('paragraph', ('halign', 'right')),
                 (self._container, dict(tag='p', style='text-align: right;'))),
                (('paragraph', ('halign', 'center')),
                 (self._container, dict(tag='p', style='text-align: center;'))),
                (('paragraph', ('halign', 'justify')),
                 (self._container, dict(tag='p', style='text-align: justify;'))),
                ('paragraph', (self._container, dict(tag='p'))),
                (('list', ('order', 'lower-alpha')),
                 (self._container, dict(tag='ol', style='list-style-type: lower-alpha;'))),
                (('list', ('order', 'upper-alpha')),
                 (self._container, dict(tag='ol', style='list-style-type: upper-alpha;'))),
                (('list', ('order', 'numeric')), (self._container, dict(tag='ol'))),
                ('list', (self._container, dict(tag='ul'))),
                ('section', self._section),
                ('definitions', self._definitions),
                ('anchor', self._anchor),
                ('link', self._link),
                ('audio', (self._media, dict(class_=lcg.InlineAudio))),
                ('video', (self._media, dict(class_=lcg.InlineVideo))),
                ('image', self._image),
                ('table', self._table),
                ('row', (self._container, dict(class_=lcg.TableRow))),
                ('cell', self._table_cell),
            )

        def __init__(self):
            XMLProcessor.Transformer.__init__(self)
            self._section_level = 1

        def _make_content(self, tag, attributes, children, text=None):
            attr = {}
            for k, v in attributes.items():
                if v is not None:
                    attr[k] = v
            element = xml.etree.ElementTree.Element(tag, attr)
            last = element
            i = 0
            children = list(children)
            while children:
                c = children.pop(0)
                if isinstance(c, basestring):
                    if last is element:
                        last.text = (last.text or '') + c
                    else:
                        last.tail = (last.tail or '') + c
                elif isinstance(c, (tuple, list)):
                    children = list(c) + children
                else:
                    element.insert(i, c)
                    last = c
                    i += 1
            if text is not None:
                element.text = text + (element.text or '')
            return element

        def _container(self, element, followers, tag=None, **kwargs):
            content = self._transform_sub(element)
            if tag is None:
                tag = element.attrib['tag']
            return self._make_content(tag, kwargs, content, element.text)

        def _text(self, element, followers):
            return element.text

        def _section(self, element, followers):
            children = list(element)
            if children and children[0].tag == 'heading':
                heading = self._transform_sub(children[0])
                children = children[1:]
            else:
                heading = ()
            self._section_level += 1
            content = self._transform_sub(element, children)
            self._section_level -= 1
            tag = 'h%d' % (self._section_level,)
            return [self._make_content(tag, {}, heading)] + list(content)

        def _definitions(self, element, followers):
            items = self._transform_sub(element)
            html_items = []
            for i in items:
                term, definition = list(i)
                term.tag = 'dt'
                definition.tag = 'dd'
                html_items += [term, definition]
            return self._make_content('dl', {}, html_items)

        def _anchor(self, element, followers):
            name = element.attrib['name']
            text = element.text
            return self._make_content('a', dict(name=name), (), text)

        def _link(self, element, followers):
            return self._make_content('a', dict(href=element.attrib['target']),
                                      self._transform_sub(element))

        def _media(self, element, followers):
            media_class = {'audio': 'lcg-audio',
                           'video': 'lcg-video'}.get(element.tag)
            return self._make_content('a', {'class': media_class, 'href': element.attrib['target']},
                                      self._transform_sub(element))

        def _image(self, element, followers):
            alignment = {lcg.InlineImage.LEFT: 'left',
                         lcg.InlineImage.RIGHT: 'right'}.get(element.attrib.get('align'))
            return self._make_content('img', dict(src=element.attrib['target'], align=alignment),
                                      self._transform_sub(element))

        def _table(self, element, followers):
            content = self._transform_sub(element)
            for i in range(len(content)):
                if content[i].attrib.get('head') != '1':
                    break
            head = self._make_content('thead', {}, content[:i])
            body = self._make_content('tbody', {}, content[i:])
            transformed = self._make_content('table', {}, (head, body,))
            title = element.attrib.get('title')
            if title is not None:
                caption = self._make_content('caption', {}, (), title)
                transformed.insert(0, caption)
            return transformed

        def _table_cell(self, element, followers):
            tag = 'th' if element.attrib.get('heading') == '1' else 'td'
            attributes = {}
            alignment = {'left': 'text-align: left;',
                         'right': 'text-align: right;',
                         'center': 'text-align: center;'}.get(element.attrib.get('align'))
            if alignment:
                attributes['align'] = alignment
            self._make_element(tag, attributes, self._transform_sub(element))

        def _mathml(self, element, followers):
            transformed = xml.etree.ElementTree.XML(element.text)
            for e in transformed.getiterator():
                if e.tag.startswith('{'):
                    e.tag = e.tag[e.tag.find('}') + 1:]
            return transformed

    def transform(self, data):
        transformed = super(XML2HTML, self).transform(data)
        tree = xml.etree.ElementTree.ElementTree(transformed)
        f = io.BytesIO()
        tree.write(f, 'utf-8', method=None)
        return f.getvalue().decode('utf-8')


class HTML2XML(Processor):
    """Processor transforming editor HTML to LCG XML.

    This is just a base class, intended to be subclassed for each supported
    HTML editor.

    """

    class Parser(html.parser.HTMLParser, Processor.Parser):

        def reset(self):
            html.parser.HTMLParser.reset(self)
            self._hp_tree = xml.etree.ElementTree.Element('html')
            self._hp_elements = [self._hp_tree]
            self._hp_open_tags = []
            self._hp_current_text = ''
            self._hp_raw = False

        def _hp_finish_text(self):
            if self._hp_current_text:
                element = xml.etree.ElementTree.SubElement(self._hp_elements[-1], '_text')
                element.text = self._hp_current_text
                self._hp_current_text = ''

        def handle_starttag(self, tag, attrs):
            if self._hp_raw:
                self._hp_current_text += self.get_starttag_text()
                return
            self._hp_finish_text()
            if tag == 'math':
                if not self._hp_raw and self._hp_current_text:
                    element = xml.etree.ElementTree.SubElement(self._hp_elements[-1], '_text')
                    element.text = self._hp_current_text
                self._hp_raw = True
            if self._hp_raw:
                self._hp_current_text = self.get_starttag_text()
            element = xml.etree.ElementTree.SubElement(self._hp_elements[-1], tag, dict(attrs))
            self._hp_elements.append(element)
            self._hp_open_tags.append(tag)

        def handle_endtag(self, tag):
            if self._hp_raw:
                self._hp_current_text += '</%s>' % (tag,)
                if tag != self._hp_open_tags[-1]:
                    return
            while self._hp_open_tags[-1] != tag:
                self.handle_endtag(self._hp_open_tags[-1])
            if self._hp_raw:
                self._hp_elements[-1].text = self._hp_current_text
                self._hp_current_text = ''
            else:
                self._hp_finish_text()
            self._hp_elements.pop()
            self._hp_open_tags.pop()
            self._hp_raw = False

        def handle_data(self, data):
            self._hp_current_text += data

        def handle_charref(self, name):
            num = name.lstrip('&#').rstrip(';')
            expanded = chr(int(num))
            self.handle_data(expanded)

        def handle_entityref(self, name):
            if self._hp_raw:
                self._handle_data('&' + name + ';')
            else:
                expanded = html.entities.entitydefs[name]
                if expanded[0] == b'&' and expanded[-1] == b';':
                    self.handle_charref(expanded)
                else:
                    self.handle_data(expanded.decode('iso-8859-1'))

        def close(self):
            while self._open_tags:
                self.handle_endtag(self._open_tags[-1])
            html.parser.HTMLParser.close()

        def _hp_strip(self, tree):
            if tree.tag == 'pre':
                return
            children = list(tree)
            if len(children) > 0:
                first = children[0]
                if first.tag == '_text':
                    first.text = first.text.lstrip()
            if len(children) > 1:
                last = children[-1]
                if last.tag == '_text':
                    last.text = last.text.rstrip()
            for c in children:
                if c.tag != '_text':
                    self._hp_strip(c)

        def lcg_parse(self, html):
            html = self._text_process(html)
            self.feed(html)
            self._hp_strip(self._hp_tree)
            return self._hp_tree

    class Transformer(Processor.Transformer):

        def __init__(self):
            Processor.Transformer.__init__(self)
            self._in_table_heading = False

        def _matchers(self):
            return (
                (('div', ('style', '.*page-break-after: always;.*')),
                 (self._single, dict(tag='new-page'))),
                ('br', (self._single, dict(tag='new-line'))),
                ('(html|div|span|strike|li|dt|dd)', self._container),
                (('p', ('style', 'text-align: right;')),
                 (self._container, dict(tag='paragraph', halign='right'))),
                (('p', ('style', 'text-align: center;')),
                 (self._container, dict(tag='paragraph', halign='center'))),
                (('p', ('style', 'text-align: justify;')),
                 (self._container, dict(tag='paragraph', halign='justify'))),
                ('p', (self._container, dict(tag='paragraph'))),
                ('blockquote', (self._container, dict(tag='citation'))),
                ('strong', (self._container, dict(tag='strong'))),
                ('em', (self._container, dict(tag='emphasized'))),
                ('u', (self._container, dict(tag='underlined'))),
                ('sub', (self._container, dict(tag='subscript'))),
                ('sup', (self._container, dict(tag='superscript'))),
                ('h[0-9]', self._section),
                ('pre', (self._text, dict(tag='preformatted'))),
                ('ul', (self._list, dict(order=None))),
                (('ol', ('style', '.* lower-alpha;.*')), (self._list, dict(order='lower-alpha'))),
                (('ol', ('style', '.* upper-alpha;.*')), (self._list, dict(order='upper-alpha'))),
                ('ol', (self._list, dict(order='numeric'))),
                ('dl', self._definition_list),
                (('a', ('name', '.+')), self._anchor),
                (('a', ('class', 'lcg-audio')), (self._media, dict(tag='audio'))),
                (('a', ('class', 'lcg-video')), (self._media, dict(tag='video'))),
                ('a', self._link),
                ('table', self._table),
                ('tr', self._table_row),
                ('t[dh]', self._table_cell),
                ('hr', (self._single, dict(tag='separator'))),
                ('math', (self._plain, dict(tag='mathml'))),
                ('img', self._image),
                ('_text', self._text),
            )

        def _first_text(self, element):
            """Return first text found in 'element'.

            If element doesn't contain non-empty text then look for the text in
            its children (including their whole subtrees but not attributes) in
            depth-first order.  If no text is found anywhere, return an empty
            string.

            Arguments:

              element -- 'xml.etree.ElementTree.Element' instance

            """
            text = element.text
            if text:
                return text
            for c in element:
                text = self._first_text(c)
                if text:
                    return text
            return ''

        def _plain_text(self, element):
            """Return all text found in element.

            Take the text of the element and all texts of its children
            including the whole subtrees.  Concatenate the texts in depth-first
            order and return the resulting text (empty string if no text is
            found).  Texts are taken just from element texts, not from
            attributes.

            Arguments:

              element -- 'xml.etree.ElementTree.Element' instance

            """
            text = element.text or ''
            for c in element:
                text += self._plain_text(c)
            return text

        def _transform_sub(self, obj, nowhitespace=True):
            obj = list(obj)
            content = []
            while obj:
                c_ = obj.pop(0)
                content.append(self.transform(c_, obj))
            if nowhitespace:
                content = [c for c in content if c.tag != 'text' or c.text.strip()]
            return content

        def _container(self, element, followers, tag='container', **kwargs):
            content = self._transform_sub(element)
            return self._make_content(tag, dict(tag=element.tag, **kwargs), content)

        def _section(self, element, followers):
            level = element.tag[1]
            section_children = []
            while followers:
                c = followers[0]
                if c.tag[0] == 'h' and c.tag[1] <= level:
                    break
                section_children.append(c)
                followers.pop(0)
            transformed_title = self._transform_sub(element)
            if not transformed_title:
                transformed_title = self._make_content('text', {}, (), u'')
            title_content = self._make_content('heading', {}, transformed_title)
            text_title = self._plain_text(element)
            content = [title_content] + self._transform_sub(section_children)
            return self._make_content('section', dict(title=text_title), content)

        def _list(self, element, followers, order=None):
            items = self._transform_sub(element)
            return self._make_content('list', dict(order=order), items)

        def _definition_list(self, element, followers):
            items = self._transform_sub(element)
            paired_items = []
            while items:
                term = items.pop(0)
                definition = items.pop(0)
                paired_items.append(self._make_content('definition', {}, (term, definition,)))
            return self._make_content('definitions', {}, paired_items)

        def _text(self, element, followers, tag='text'):
            return self._make_content(tag, {}, (), self._first_text(element))

        def _plain(self, element, followers, tag='text'):
            return self._make_content(tag, {}, (), element.text)

        def _single(self, element, followers, tag='container'):
            return self._make_content(tag, {}, ())

        def _anchor(self, element, followers):
            name = element.attrib['name']
            text = self._first_text(element)
            return self._make_content('anchor', dict(anchor=name), (), text)

        def _link(self, element, followers):
            if 'enlarge-image' in element.attrib.get('class', ''):
                # Temporary hack to ignore link around images enlarged on click.
                return self._make_content('container', dict(hack='1'), self._transform_sub(element))
            else:
                content = self._transform_sub(element)
                resource = element.attrib.get('data-lcg-resource')
                if resource:
                    target = resource
                else:
                    target = element.attrib['href']
                return self._make_content('link', dict(target=target), content)

        def _media(self, element, followers, tag=None, uri=None, **kwargs):
            resource = element.attrib.get('data-lcg-resource')
            if resource:
                target = resource
            else:
                target = uri or element.attrib['href']
            basename = target.split('/')[-1].rsplit('.', 1)[0]
            return self._make_content(tag, dict(target=target, name=basename, **kwargs), ())

        def _image(self, element, followers):
            alignment = element.attrib.get('align')
            if alignment not in ('left', 'right',):
                alignment = ''
            return self._media(element, followers, tag='image',
                               uri=element.attrib['src'], align=alignment)

        def _table(self, element, followers):
            content = []
            title = None
            for c in element:
                tag = c.tag
                if tag == 'caption':
                    title = self._first_text(c).strip()
                elif tag == 'thead':
                    self._in_table_heading = True
                    content += self._transform_sub(c)
                    self._in_table_heading = False
                elif tag == 'tbody':
                    content += self._transform_sub(c)
            return self._make_content('table', dict(title=title), content)

        def _table_row(self, element, followers):
            head = '1' if self._in_table_heading else '0'
            return self._container(element, followers, tag='row', head=head)

        def _table_cell(self, element, followers):
            style = element.attrib.get('style', '')
            align = None
            if style.find('text-align: left;') >= 0:
                align = 'left'
            elif style.find('text-align: right;') >= 0:
                align = 'right'
            elif style.find('text-align: center;') >= 0:
                align = 'center'
            heading = '1' if element.tag == 'th' else '0'
            return self._make_content('cell', dict(align=align, heading=heading),
                                      self._transform_sub(element))

    def transform(self, data):
        transformed = super(HTML2XML, self).transform(data)
        tree = xml.etree.ElementTree.ElementTree(transformed)
        f = io.BytesIO()
        tree.write(f, 'utf-8', method=None)
        return f.getvalue().decode('utf-8')


# Utility functions


def data2content(data):
    """Convenience function to convert LCG XML to LCG Content.

    Arguments:

      data -- unicode containing input LCG XML

    Return corresponding 'Content' instance.

    See 'XML2Content' for more information and information about LCG XML.

    """
    processor = XML2Content()
    return processor.transform(data)


def data2html(data, processor):
    """Convenience function to convert LCG XML to LCG Content.

    Arguments:

      data -- unicode containing input LCG XML
      processor -- class to use for the conversion; subclass of 'XML2HTML'

    Return corresponding HTML unicode.

    See 'XML2HTML' for more information.

    """
    processor = processor()
    return processor.transform(data)


def html2data(html, processor):
    """Convenience function to convert editor HTML to LCG XML.

    Arguments:

      html -- unicode containing input HTML
      processor -- class to use for the conversion; subclass of 'HTML2XML'

    Return corresponding LCG XML unicode.

    See 'HTML2XML' for more information.

    """
    processor = processor()
    return processor.transform(html)
