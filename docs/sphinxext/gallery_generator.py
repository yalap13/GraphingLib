"""
Sphinx plugin to run example scripts and create a gallery page.

Lightly modified from the seaborn project.

"""

import os
import os.path as op
import re
import glob
import token
import tokenize
import shutil
import warnings

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


# Python 3 has no execfile
def execfile(filename, globals=None, locals=None):
    with open(filename, "rb") as fp:
        exec(compile(fp.read(), filename, "exec"), globals, locals)


RST_TEMPLATE = """

.. currentmodule:: graphinglib

.. _{sphinx_tag}:

{docstring}

.. image:: {img_file}

**GraphingLib components used:** {components}

.. literalinclude:: {fname}
    :lines: {end_line}-

"""


INDEX_TEMPLATE = """
:html_theme.sidebar_secondary.remove:

.. raw:: html

    <style type="text/css">
    .gallery-container {{
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        padding: 20px;
    }}
    .thumb {{
        position: relative;
        float: left;
        width: 180px;
        height: 180px;
        margin: 5px;
    }}
    .thumb img {{
        position: absolute;
        display: inline;
        left: 0;
        width: 170px;
        height: 170px;
        opacity: 1.0;
        filter: alpha(opacity=100); /* For IE8 and earlier */
        transition: filter 0.3s, opacity 0.3s;
    }}
    .thumb:hover img {{
        -webkit-filter: blur(3px);
        -moz-filter: blur(3px);
        -o-filter: blur(3px);
        -ms-filter: blur(3px);
        filter: blur(3px);
        opacity: 1.0;
        filter: alpha(opacity=100); /* For IE8 and earlier */
    }}
    html[data-theme=dark] .thumb:hover img {{
        -webkit-filter: blur(3px);
        -moz-filter: blur(3px);
        -o-filter: blur(3px);
        -ms-filter: blur(3px);
        filter: blur(3px);
        opacity: 1.0;
        filter: alpha(opacity=100); /* For IE8 and earlier */
    }}
    .thumb span {{
        position: absolute;
        display: flex;
        align-items: center;
        justify-content: center;
        left: 0;
        width: 170px;
        height: 170px;
        background: rgba(0, 0, 0, 0.4);
        color: #fff;
        visibility: hidden;
        opacity: 0;
        z-index: 100;
        transition: visibility 0s, opacity 0.3s;
    }}
    .thumb p {{
        font-size: 110%;
        color: #fff;
        margin: 0;
        text-align: center;
    }}
    .thumb:hover span {{
        visibility: visible;
        opacity: 1;
    }}
    .caption {{
        position: absolute;
        width: 180px;
        top: 170px;
        text-align: center !important;
    }}
    @media (max-width: 600px) {{
        .gallery-container {{
            padding: 7px;
        }}
        .thumb {{
            width: 160px;
            height: 160px;
            margin: 3px;
        }}
        .thumb img {{
            width: 150px;
            height: 150px;
        }}
        .thumb span {{
            width: 150px;
            height: 150px;
        }}
        .caption {{
            width: 160px;
            top: 150px;
        }}
    }}
    </style>

.. _{sphinx_tag}:

Example gallery
===============

{toctree}

.. raw:: html

    <div class="gallery-container">
    {contents}
    </div>

.. raw:: html

    <div style="clear: both"></div>
"""


def create_thumbnail(infile, thumbfile):
    baseout, extout = op.splitext(thumbfile)
    im = matplotlib.image.imread(infile)

    percent_keep = 0.92
    height, width, _ = im.shape
    if height <= width:
        to_cut = (width - height * percent_keep) / 2
        if int(to_cut) != to_cut:
            thumb = im[
                : int(percent_keep * height), int(to_cut) : width - int(to_cut + 1), :
            ]
        else:
            thumb = im[
                : int(percent_keep * height), int(to_cut) : width - int(to_cut), :
            ]
    else:
        to_cut = (height * percent_keep - width) / 2
        if int(to_cut) != to_cut:
            thumb = im[int(to_cut) : int(height * percent_keep) - int(to_cut + 1), :, :]
        else:
            thumb = im[int(to_cut) : int(height * percent_keep) - int(to_cut), :, :]

    border = int(np.ceil(0.02 * thumb.shape[0]))
    thumb[-border:, :, :3] = thumb[:border, :, :3] = np.array(
        [105 / 255, 123 / 255, 150 / 255]
    )
    thumb[:, :border, :3] = thumb[:, -border:, :3] = np.array(
        [105 / 255, 123 / 255, 150 / 255]
    )

    new_height, new_width, _ = thumb.shape

    dpi = 100
    fig = plt.figure(figsize=(new_width / dpi, new_height / dpi), dpi=dpi)

    ax = fig.add_axes([0, 0, 1, 1], aspect="auto", frameon=False, xticks=[], yticks=[])
    if all(thumb.shape):
        ax.imshow(thumb, aspect="auto", resample=True, interpolation="bilinear")
    else:
        warnings.warn(f"Bad thumbnail crop. {thumbfile} will be empty.")
    fig.savefig(thumbfile, dpi=dpi)
    return fig


def indent(s, N=4):
    """indent a string"""
    return s.replace("\n", "\n" + N * " ")


class ExampleGenerator:
    """Tools for generating an example page from a file"""

    def __init__(self, filename, target_dir):
        self.filename = filename
        self.target_dir = target_dir
        self.thumbloc = 0.5, 0.5
        self.extract_docstring()
        with open(filename) as fid:
            self.filetext = fid.read()

        outfilename = op.join(target_dir, self.rstfilename)

        # Only actually run it if the output RST file doesn't
        # exist or it was modified less recently than the example
        file_mtime = op.getmtime(filename)
        if not op.exists(outfilename) or op.getmtime(outfilename) < file_mtime:
            self.exec_file()
        else:
            print(f"skipping {self.filename}")

    @property
    def dirname(self):
        return op.split(self.filename)[0]

    @property
    def fname(self):
        return op.split(self.filename)[1]

    @property
    def modulename(self):
        return op.splitext(self.fname)[0]

    @property
    def pyfilename(self):
        return self.modulename + ".py"

    @property
    def rstfilename(self):
        return self.modulename + ".rst"

    @property
    def htmlfilename(self):
        return self.modulename + ".html"

    @property
    def pngfilename(self):
        pngfile = self.modulename + ".png"
        return "_images/" + pngfile

    @property
    def thumbfilename(self):
        pngfile = self.modulename + "_thumb.png"
        return pngfile

    @property
    def sphinxtag(self):
        return self.modulename

    @property
    def pagetitle(self):
        return self.docstring.strip().split("\n")[0].strip()

    @property
    def components(self):

        objects = re.findall(r"gl\.(\w+)\(", self.filetext)
        objects = set(objects)

        refs = []
        for obj in objects:
            if obj[0].isupper():
                refs.append(f":class:`{obj}`")
            else:
                refs.append(f":func:`{obj}`")
        refs.sort()
        return ", ".join(refs)

    def extract_docstring(self):
        """Extract a module-level docstring"""
        lines = open(self.filename).readlines()
        start_row = 0
        if lines[0].startswith("#!"):
            lines.pop(0)
            start_row = 1

        docstring = ""
        first_par = ""
        line_iter = lines.__iter__()
        tokens = tokenize.generate_tokens(lambda: next(line_iter))
        for tok_type, tok_content, _, (erow, _), _ in tokens:
            tok_type = token.tok_name[tok_type]
            if tok_type in ("NEWLINE", "COMMENT", "NL", "INDENT", "DEDENT"):
                continue
            elif tok_type == "STRING":
                docstring = eval(tok_content)
                # If the docstring is formatted with several paragraphs,
                # extract the first one:
                paragraphs = "\n".join(
                    line.rstrip() for line in docstring.split("\n")
                ).split("\n\n")
                if len(paragraphs) > 0:
                    first_par = paragraphs[0]
            break

        thumbloc = None
        for i, line in enumerate(docstring.split("\n")):
            m = re.match(r"^_thumb: (\.\d+),\s*(\.\d+)", line)
            if m:
                thumbloc = float(m.group(1)), float(m.group(2))
                break
        if thumbloc is not None:
            self.thumbloc = thumbloc
            docstring = "\n".join(
                [l for l in docstring.split("\n") if not l.startswith("_thumb")]
            )

        self.docstring = docstring
        self.short_desc = first_par
        self.end_line = erow + 1 + start_row

    def exec_file(self):
        print(f"running {self.filename}")

        plt.close("all")
        my_globals = {"pl": plt, "plt": plt}
        execfile(self.filename, my_globals)

        fig = plt.gcf()
        fig.canvas.draw()
        pngfile = op.join(self.target_dir, self.pngfilename)
        thumbfile = op.join("example_thumbs", self.thumbfilename)
        self.html = f"<img src=../{self.pngfilename}>"
        fig.savefig(pngfile, dpi=75, bbox_inches="tight")

        create_thumbnail(pngfile, thumbfile)

    def toctree_entry(self):
        return f"   ./{op.splitext(self.htmlfilename)[0]}\n\n"

    def contents_entry(self):
        return (
            ".. raw:: html\n\n"
            "    <div class='thumb align-center'>\n"
            "    <a href=./{}>\n"
            "    <img src=../_static/{}>\n"
            "    <span class='thumb-label'>\n"
            "    <p>{}</p>\n"
            "    </span>\n"
            "    </a>\n"
            "    </div>\n\n"
            "\n\n"
            "".format(self.htmlfilename, self.thumbfilename, self.pagetitle)
        )


def main(app):
    static_dir = op.join(app.builder.srcdir, "_static")
    target_dir = op.join(app.builder.srcdir, "examples")
    image_dir = op.join(app.builder.srcdir, "examples/_images")
    thumb_dir = op.join(app.builder.srcdir, "example_thumbs")
    source_dir = op.abspath(op.join(app.builder.srcdir, "..", "examples"))
    if not op.exists(static_dir):
        os.makedirs(static_dir)

    if not op.exists(target_dir):
        os.makedirs(target_dir)

    if not op.exists(image_dir):
        os.makedirs(image_dir)

    if not op.exists(thumb_dir):
        os.makedirs(thumb_dir)

    if not op.exists(source_dir):
        os.makedirs(source_dir)

    banner_data = []

    toctree = "\n\n" ".. toctree::\n" "   :hidden:\n\n"
    contents = "\n\n"

    # Write individual example files
    for filename in sorted(glob.glob(op.join(source_dir, "*.py"))):

        ex = ExampleGenerator(filename, target_dir)

        banner_data.append(
            {
                "title": ex.pagetitle,
                "url": op.join("examples", ex.htmlfilename),
                "thumb": op.join(ex.thumbfilename),
            }
        )
        shutil.copyfile(filename, op.join(target_dir, ex.pyfilename))
        output = RST_TEMPLATE.format(
            sphinx_tag=ex.sphinxtag,
            docstring=ex.docstring,
            end_line=ex.end_line,
            components=ex.components,
            fname=ex.pyfilename,
            img_file=ex.pngfilename,
        )
        with open(op.join(target_dir, ex.rstfilename), "w") as f:
            f.write(output)

        toctree += ex.toctree_entry()
        contents += ex.contents_entry()

    if len(banner_data) < 10:
        banner_data = (4 * banner_data)[:10]

    # write index file
    index_file = op.join(target_dir, "index.rst")
    with open(index_file, "w") as index:
        index.write(
            INDEX_TEMPLATE.format(
                sphinx_tag="example_gallery", toctree=toctree, contents=contents
            )
        )


def setup(app):
    app.connect("builder-inited", main)
