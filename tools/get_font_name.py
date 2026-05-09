from fontTools.ttLib import TTFont
import argparse
from pathlib import Path


def get_font_names(font_path):
    with TTFont(font_path) as font:
        name = font["name"]

        family = name.getBestFamilyName()
        subfamily = name.getBestSubFamilyName()
        full_name = name.getBestFullName()
    return family, subfamily, full_name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("font_file", type=Path)
    args = parser.parse_args()
    family, subfamily, full_name = get_font_names(args.font_file)
    print(f"font_full_name: {full_name}")
    print(f"font_family: {family}")
    print(f"font_sub_family: {subfamily}")


if __name__ == "__main__":
    main()
