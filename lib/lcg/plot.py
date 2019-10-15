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
                 plot_labels=None, annotate=False, grid=False):
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
