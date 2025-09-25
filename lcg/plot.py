# -*- coding: utf-8 -*-

# Copyright (C) 2019-2025 Tomáš Cerha <t.cerha@gmail.com>
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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from __future__ import division

import datetime
import io
import lcg
from matplotlib import pyplot
import matplotlib.ticker
import matplotlib.dates
import os
import pandas

_ = lcg.TranslatableTextFactory('lcg')


class Line(object):
    """Representation of a plot line parameters for 'grid' and 'lines' arguments of 'LinePlot'.

    Constructor arguments:

      x: Line position for a vertical line in 'lines' argument of a 'LinePlot'.
        A value compatible with other x axis values of the plot (e.g. a
        datetime instance when x values are datetimes).  Irrelevant for 'grid'
        lines.
      y: Line position for a horizontal line in 'lines' argument of a
        'LinePlot'.  Analogical to 'x'.
      color: Line color given by 'lcg.Color' instance, hexadecimal RGB or RGBA
        representation or a X11/CSS4 color name (such as '#fa046e' or 'red').
      with: Line width in points (int or float).
      style: Line style.  One of 'solid', 'dashed', 'dashdot' or 'dotted'.
      alpha: Alpha as a float in range 0.0 (transparent) - 1.0 (solid).

    """
    def __init__(self, x=None, y=None, color=None, width=None, style=None, alpha=None):
        self.x = x
        self.y = y
        if isinstance(color, lcg.Color):
            color = tuple(float(x) / 255 for x in color.rgb())
        attr = dict(color=color, linewidth=width, linestyle=style)
        self.attr = {k: v for k, v in attr.items() if v is not None}


class BasePlot(lcg.InlineSVG):
    """Base class for embedded plot as 'lcg.Content' element.

    Plots can be created based on input data passed as a sequence of x, y
    points or a 'pandas.DataFrame' instance.  The axes automatically
    accommodate to the range present in input data.

    The plot is exported as SVG figure into the final document.  HTML and PDF
    export is supported.

    """

    def __init__(self, data, size=(250, 120), title=None, xlabel=None, ylabel=None,
                 xformatter=None, yformatter=None, legend=None, annotate=False,
                 grid=False, lines=(), plot_labels=None):
        """Arguments:

          data: 'pandas.DataFrame' instance or a sequence of sequences
            containing the data to be visualized by the plot.  If sequence,
            each item is a pair, where the first value is the x coordinate and
            the second value is the y coordinate of one graph point.  There may
            be also more y values in each item.  In this case several
            lines will appear in the plot sharing the x coordinates and
            differing y coordinates.
          size: total plot size as a pair of 'lcg.Unit' subclass instances or
            numeric values which will be converted to 'lcg.UMm'.
          title: Title to be displayed above the plot as a string.
          xlabel: x axis label as a human readable string.
          ylabel: y axis label as a human readable string.
          xformatter: x axis tick label formater as a function of three
            arguments (context, value, position), where context is the LCG
            export context, value is the matplotlib's internal value
            representation and position is the tick position numbered from 0.
            This module defines several formatter classes for most common
            cases, such as 'DateFormatter', 'DateTimeFormatter',
            'MonetaryFormatter' which respect LCG localization.
            'DateFormatter' is used automatically for the x axis if it contains
            datetime values.
          yformatter: as xformatter but for the y axis values.
          legend: optional sequence of plot labels as human readable
            strings.  Useful for distinction when there are several plots (data
            contain multiple y values).  The number of labels must correspond to
            the number of y values in 'data'.
          annotate: If True, each plot point (x, y pair present in data) will
            be labeled by the y value directly within the plot.
          grid: Controls grid lines.  May be a single value to control the
            major grid (minor is off), a tuple of two values (major, minor) or
            four values (major-x, major-y, minor-x, minor-y).  Major grid
            connects to labeled axis values, minor grid provides finer
            subdivision.  Each value may be a boolean to turn the grid on or
            off or a 'lcg.plot.Line' instance defining properties in more
            detail.
          lines: Additional vertical or horizontal lines added to the graph as
            a sequence of 'Line' instances.  Lines must define 'x' (for
            vertical lines) or 'y' (for horizontal lines) position as a value
            compatible with other values of that axis.

        """
        if not isinstance(data, pandas.DataFrame):
            data = pandas.DataFrame([x[1:] for x in data],
                                    index=[x[0] for x in data],
                                    columns=['column%d' % n for n in range(len(data[0]) - 1)])
        if not xformatter and isinstance(data.index[0], datetime.date):
            xformatter = DateFormatter()
        self._data = data
        self._size = [x if isinstance(x, lcg.Unit) else lcg.UMm(x) for x in size]
        self._title = title
        self._xlabel = xlabel
        self._ylabel = ylabel
        self._xformatter = xformatter
        self._yformatter = yformatter
        # The former (deprecated) argument name is 'plot_labels'.
        self._legend = legend or plot_labels or [None for x in data.columns]
        self._annotate = annotate
        if grid is False:
            grid = None
        elif grid is True:
            grid = (True, True, False, False)
        else:
            assert isinstance(grid, (tuple, list)), grid
            assert all(isinstance(g, (bool, Line)) for g in grid), grid
            if len(grid) == 2:
                major, minor = grid
                grid = (major, major, minor, minor)
            else:
                assert len(grid) == 4
        self._grid = grid
        assert all(isinstance(l, Line) for l in lines), lines
        self._lines = lines
        super(BasePlot, self).__init__(self._svg)

    def _plot(self, ax):
        raise NotImplementedError()

    def _svg(self, context):
        factor = context.exporter().MATPLOTLIB_RESCALE_FACTOR
        size = [x.size() * factor / 25.4 for x in self._size]
        fig, ax = pyplot.subplots(1, 1, figsize=size, sharex=True, sharey=True)
        if self._title:
            ax.set_title(self._title)
        if self._xlabel:
            ax.set_xlabel(self._xlabel)
        if self._ylabel:
            ax.set_ylabel(self._ylabel)
        if self._grid:
            for line, which, axis in zip(self._grid, ('major', 'major', 'minor', 'minor'),
                                         ('x', 'y', 'x', 'y')):
                if line is True:
                    kwargs = dict(zorder=0, color='#dddddd' if which == 'major' else '#eeeeee')
                elif line is False:
                    kwargs = dict(visible=False)
                else:
                    kwargs = dict(zorder=0, **line.attr)
                if line and which == 'minor':
                    ax.minorticks_on()
                ax.grid(which=which, axis=axis, **kwargs)
        for line in self._lines:
            if line.x:
                ax.axvline(x=line.x, **line.attr)
            else:
                ax.axhline(y=line.y, **line.attr)
        xformatter, yformatter = self._xformatter, self._yformatter
        if isinstance(xformatter, DateFormatter):
            # Automatically rotate date labels if necessary to avoid overlapping.
            fig.autofmt_xdate()
        for formatter, axis in ((xformatter, ax.xaxis), (yformatter, ax.yaxis)):
            if formatter:
                axis.set_major_formatter(matplotlib.ticker.FuncFormatter(
                    lambda value, position, f=formatter: f(context, value, position)
                ))
        self._plot(ax)
        if any(self._legend):
            ax.legend()
        f = io.StringIO()
        fig.savefig(f, format='svg')
        pyplot.close(fig)
        return f.getvalue()


class BarPlot(BasePlot):
    """Bar plot to be used within LCG content.

    Input data passed to the constructor should represent atomic values (a
    sequence of (x, y) values is the simplest use case -- see the constructor
    arguments documentation).  More y values (represented by separate bars for
    each x value) are also supported.

    """

    def _plot(self, ax):
        data = self._data
        n = len(data.columns)
        width = 0.8 / n
        xticks = range(len(data))
        for i, col, label in zip(range(len(data)), data.columns, self._legend):
            xpos = [x + (i + 1 - (n + 1) / 2) * width for x in xticks]
            coldata = getattr(data, col)
            ax.bar(xpos, coldata, width=width, zorder=3, label=label)
            if self._annotate:
                for x, y in zip(xpos, coldata):
                    ax.annotate(y, xy=(x, y), verticalalignment='bottom', horizontalalignment='center')
        ax.set_xticks(xticks)
        labels = [data.index[x] for x in xticks]
        if isinstance(labels[0], datetime.date):
            formatter = ax.xaxis.get_major_formatter()
            labels = [formatter(label) for label in matplotlib.dates.date2num(labels)]
        ax.set_xticklabels(labels)


class LinePlot(BasePlot):
    """Line plot to be used within LCG content.

    Several plot lines can be present in a single plot.

    The plot is exported as SVG figure into the final document.  Only HTML
    export is currently supported.

    """

    def _plot(self, ax):
        data = self._data
        for col, label in zip(data.columns, self._legend):
            ax.plot(data.index, getattr(data, col), label=label)
        if self._annotate:
            for col in data.columns:
                for i, value in enumerate(getattr(data, col)):
                    ax.annotate(value, xy=(data.index[i], value), verticalalignment='bottom')


class LocalizingFormatter(object):
    """Common base class for LCG locale aware formatters."""

    def _localizable(self, value):
        raise NotImplementedError()

    def __call__(self, context, value, position):
        return context.localize(self._localizable(value))


class DateTimeFormatter(LocalizingFormatter):
    """Formats plot axis labels using LCG's locale aware datetime formatting.

    Use instances of this class for the 'xformatter' and 'yformatter'
    constructor arguments of 'LinePlot'.

    """
    def __init__(self, leading_zeros=False):
        self._kwargs = dict(leading_zeros=leading_zeros)

    def _localizable(self, value):
        # Note, matplotlib returns a datetime with UTC timezone, but we
        # want to avoid timezone conversion (or seeing the timezone on output
        # when export context timezone is not set).
        dt = matplotlib.dates.num2date(value).replace(tzinfo=None)
        return lcg.LocalizableDateTime(dt, **self._kwargs)


class DateFormatter(DateTimeFormatter):
    """Formats plot axis labels using LCG's locale aware date formatting.

    Use instances of this class for the 'xformatter' and 'yformatter'
    constructor arguments of 'LinePlot'.

    """
    def __init__(self, leading_zeros=False):
        self._kwargs = dict(leading_zeros=leading_zeros, show_time=False)


class DecimalFormatter(LocalizingFormatter):
    """Formats plot axis labels using LCG's locale aware numerical formatting.

    Use instances of this class for the 'xformatter' and 'yformatter'
    constructor arguments of 'LinePlot'.

    """

    _UNITS = tuple(reversed((
        # Translators: Abbreviation for a million (10 ** 6).
        (10 ** 6, _("mil.")),
        # Translators: Abbreviation for a billion (10 ** 9).
        (10 ** 9, _("bil.")),
        # Translators: Abbreviation for a trillion (10 ** 12).
        (10 ** 12, _("tril.")),
    )))
    _LOCALIZABLE = lcg.Decimal

    def __init__(self, abbreviate=False, precision=None):
        """Arguments:

          abbreviate: iff True, the trailing zeros in large numbers will be
            abbreviated to "mil.", "bil." or "tril." if possible.  See class
            docstring for details.
          precision: if not None, all numbers will have given number of digits
            after the decimal point.  If None, the decimal point is only
            present when there are any non-zero digits.  Note that it must be
            None in order to allow 'abbreviate' to work.

        """
        self._abbreviate = abbreviate
        self._precision = precision

    def _localizable(self, value):
        unit = None
        if self._precision is not None:
            precision = self._precision
        elif value % 1 == 0:
            value = int(value)
            if self._abbreviate:
                for (amount, u) in self._UNITS:
                    # Prefer 1,234,000 over 1.234 mil. and abbreviate only when there are
                    # at most 2 significant digits, such as 1.23 mil.  This does not apply
                    # for higher levels, so 1.234 bil. is better than 1,234 mil.
                    precision = 2 if amount == 10 ** 6 else 3
                    if value >= amount and value % (amount / 10 ** precision) == 0:
                        value /= float(amount)
                        unit = u
                        while precision and int((10 ** precision) * value) % 10 == 0:
                            precision -= 1
                        break
                else:
                    precision = 0
            else:
                precision = 0
        else:
            precision = 2
        result = self._LOCALIZABLE(value, precision=precision)
        if unit:
            result = lcg.concat(result, u'\xa0', unit)
        return result


class MonetaryFormatter(DecimalFormatter):
    """Formats plot axis labels using LCG's locale aware monetary formatting.

    Use instances of this class for the 'xformatter' and 'yformatter'
    constructor arguments of 'LinePlot'.

    """
    _LOCALIZABLE = lcg.Monetary
