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
import pandas


class LinePlot(lcg.Content):
    """Embedded line plot as 'lcg.Content' element.

    Line plot can be created based on input data passed as a sequence of x, y
    points or a 'pandas.DataFrame' instance.  The x, y points present in input
    data are connected by a line.  The axes automatically accommodate to
    the range present in input data.  Several plot lines can be present in a
    single plot.  Plot data can be also passed as .

    The plot is exported as SVG figure into the final document.  Only HTML
    export is currently supported.

    """

    def __init__(self, data, size=(10, 6), title=None, xlabel=None, ylabel=None,
                 plot_labels=None, annotate=False):
        """Arguments:

          data: 'pandas.DataFrame' instance or a sequence of sequences
            containing the data to be visualized by the plot.  If sequence,
            each item is a pair, where the first value is the x coordinate and
            the second value is the y coordinate of one graph point.  There may
            be also more y values in each item.  In this case several
            lines will appear in the plot sharing the x coordinates and
            differing y coordinates.
          size: total plot size as a pair of numerical values in inches.
          title: Title to be displayed above the plot as a string.
          xlabel: x axis label as a human readable string.
          ylabel: y axis label as a human readable string.
          plot_labels: optional sequence of plot line labels as human readable
            strings.  Mostly useful for distinction when there are several plot
            lines.  The number of labels must correspond to the number of y
            values in 'data'.
          annotate: If True, each plot point (x, y pair present in data) will
            be labeled by the y value directly within the plot.

        """
        if not isinstance(data, pandas.DataFrame):
            data = pandas.DataFrame([x[1:] for x in data],
                                    index=[x[0] for x in data],
                                    columns=['column%d' % n for n in range(len(data[0]) - 1)])
        self._dataframe = data
        self._size = size
        self._title = title
        self._xlabel = xlabel
        self._ylabel = ylabel
        self._plot_labels = plot_labels
        self._annotate = annotate

    def export(self, context):
        g = context.generator()
        df = self._dataframe
        fig, ax = pyplot.subplots(1, 1, figsize=self._size, sharex=True, sharey=True)
        for col, label in zip(df.columns, self._plot_labels or [None for x in df.columns]):
            ax.plot(df.index, getattr(df, col), label=label)
        if isinstance(df.index[0], datetime.date):
            # Set locale specific date format.
            import matplotlib.dates
            formatter = matplotlib.dates.DateFormatter(context.locale_data().date_format)
            ax.xaxis.set_major_formatter(formatter)
            # Automatically rotate date labels if necessary to avoid overlapping.
            fig.autofmt_xdate()
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
        f = io.StringIO()
        fig.savefig(f, format='svg')
        return g.noescape(f.getvalue())
