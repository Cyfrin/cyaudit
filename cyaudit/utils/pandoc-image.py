#!/usr/bin/env python3
"""A pandoc filter that has the LaTeX writer use markdown alt text for image
captions.

Usage:
    pandoc --filter ./pandoc-image.py -o myfile.tex myfile.md
"""

from pandocfilters import RawBlock, toJSONFilter


def gfm_img_to_captioned_figure(key, value, format, meta):
    if key == "Para":
        for item in value:
            if item["t"] == "Image":
                # Extract alt text, source (src), and title from the image
                alt_text = item["c"][1]
                src = item["c"][2][0]
                # Convert alt text list to string
                alt_text_str = " ".join(
                    [str(x["c"]) for x in alt_text if x["t"] == "Str"]
                )

                latex_figure = f"""\\begin{{figure}}[!htbp]
\\centering
\\includegraphics{{{src}}}
\\caption{{{alt_text_str}}}
\\end{{figure}}
\\FloatBarrier"""

                return RawBlock("latex", latex_figure)


if __name__ == "__main__":
    toJSONFilter(gfm_img_to_captioned_figure)
