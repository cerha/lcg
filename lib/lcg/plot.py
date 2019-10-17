# -*- coding: utf-8 -*-

# Copyright (C) 2019 Tomáš Cerha <t.cerha@gmail.com>
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

import datetime
import io
import lcg
from matplotlib import pyplot
import matplotlib.ticker
import matplotlib.dates
import pandas

_ = lcg.TranslatableTextFactory('lcg')


class LinePlot(lcg.InlineSVG):
    """Embedded line plot as 'lcg.Content' element.

    Line plot can be created based on input data passed as a sequence of x, y
    points or a 'pandas.DataFrame' instance.  The x, y points present in input
    data are connected by a line.  The axes automatically accommodate to
    the range present in input data.  Several plot lines can be present in a
    single plot.  Plot data can be also passed as .

    The plot is exported as SVG figure into the final document.  Only HTML
    export is currently supported.

    """

    def __init__(self, data, size=(250, 120), title=None, xlabel=None, ylabel=None,
                 xformatter=None, yformatter=None, plot_labels=None, annotate=False,
                 grid=False):
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
          plot_labels: optional sequence of plot line labels as human readable
            strings.  Mostly useful for distinction when there are several plot
            lines.  The number of labels must correspond to the number of y
            values in 'data'.
          annotate: If True, each plot point (x, y pair present in data) will
            be labeled by the y value directly within the plot.
          grid: Controls grid lines.  May be True, to turn on the major grid or
            False to turn it off (default).  May also be a tuple of two values
            where the first value controls the major grid and the second value
            controls the minor grid.  Major grid connects to labeled axis
            values, minor grid provides finer subdivision.  Each value may also
            be a dictionary defining matplotlib's Line2D properties, such as:
            dict(color='#a0a0a0', linestyle=':', alpha=0.3).  Use with caution
            to aviod dependency on specific matplotlib versions.

        """
        if not isinstance(data, pandas.DataFrame):
            data = pandas.DataFrame([x[1:] for x in data],
                                    index=[x[0] for x in data],
                                    columns=['column%d' % n for n in range(len(data[0]) - 1)])
        self._dataframe = data
        self._size = [x if isinstance(x, lcg.Unit) else lcg.UMm(x) for x in size]
        self._title = title
        self._xlabel = xlabel
        self._ylabel = ylabel
        self._xformatter = xformatter
        self._yformatter = yformatter
        self._plot_labels = plot_labels
        self._annotate = annotate
        if isinstance(grid, tuple):
            self._major_grid, self._minor_grid = grid
        else:
            self._major_grid, self._minor_grid = grid, False
        super(LinePlot, self).__init__(self._svg)

    def _svg(self, context):
        df = self._dataframe
        factor = context.exporter().MATPLOTLIB_RESCALE_FACTOR
        size = [x.size() * factor / 25.4 for x in self._size]
        fig, ax = pyplot.subplots(1, 1, figsize=size, sharex=True, sharey=True)
        for col, label in zip(df.columns, self._plot_labels or [None for x in df.columns]):
            ax.plot(df.index, getattr(df, col), label=label)
        xformatter, yformatter = self._xformatter, self._yformatter
        if not xformatter and isinstance(df.index[0], datetime.date):
            xformatter = DateFormatter()
            # Automatically rotate date labels if necessary to avoid overlapping.
            fig.autofmt_xdate()
        for formatter, axis in ((xformatter, ax.xaxis), (yformatter, ax.yaxis)):
            if formatter:
                axis.set_major_formatter(matplotlib.ticker.FuncFormatter(
                    lambda value, position, formatter=formatter: formatter(context, value, position)
                ))
        if self._title:
            pyplot.title(self._title)
        if self._xlabel:
            pyplot.xlabel(self._xlabel)
        if self._ylabel:
            pyplot.ylabel(self._ylabel)
        if self._plot_labels:
            ax.legend()
        if self._annotate:
            for col in df.columns:
                for i, value in enumerate(getattr(df, col)):
                    x = df.index[i]
                    ax.annotate(value, xy=(x, value), textcoords='data')
        if self._major_grid:
            kwargs = (self._major_grid if isinstance(self._major_grid, dict)
                      else dict(color='#dddddd'))
            pyplot.grid(b=True, which='major', **kwargs)
        if self._minor_grid:
            kwargs = (self._minor_grid if isinstance(self._minor_grid, dict)
                      else dict(color='#eeeeee'))
            pyplot.minorticks_on()
            pyplot.grid(b=True, which='minor', **kwargs)
        f = io.StringIO()
        fig.savefig(f, format='svg')
        return f.getvalue()


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


# TODO: This belongs to test.py in the python3 branch, but we temporarily
# keep it here until python3 is merged to master to prevent merge conflicts.

def _test_formatter(formatter, pairs):
    exporter = lcg.HtmlExporter()
    context = exporter.context(None, 'en')
    for number, formatted in pairs:
        assert formatter(context, number, 0).replace(u'\xa0', ' ') == formatted


def test_decimal_formatter():
    _test_formatter(lcg.plot.DecimalFormatter(), (
        (1.0, '1'),
        (3.4, '3.40'),
        (120000, '120,000'),
        (2300000, '2,300,000'),
        (4234500000000, '4,234,500,000,000'),
    ))


def test_decimal_formatter_with_precision():
    _test_formatter(lcg.plot.DecimalFormatter(precision=3), (
        (1.0, '1.000'),
        (3.4, '3.400'),
        (1200, '1,200.000'),
    ))


def test_abbreviating_monetary_formatter():
    _test_formatter(lcg.plot.MonetaryFormatter(abbreviate=True), (
        (140000, '140,000'),
        (2400000, '2.4 mil.'),
        (3340000, '3.34 mil.'),
        (4341000, '4,341,000'),
        (5345100, '5,345,100'),
        (6500000000, '6.5 bil.'),
        (7530000000, '7.53 bil.'),
        (8532000000, '8.532 bil.'),
        (9000000000000, '9 tril.'),
        (1100000000000, '1.1 tril.'),
        (2120000000000, '2.12 tril.'),
        (3123000000000, '3.123 tril.'),
        (4123400000000, '4,123.400 bil.'),
        (5 * 10 ** 12, '5 tril.'),
    ))
