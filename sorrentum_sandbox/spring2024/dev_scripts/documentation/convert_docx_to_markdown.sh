#!/bin/bash -xe

FILE_NAME=docs/coding/tmp

mv /Users/saggese/Downloads/Blank.docx $FILE_NAME.docx
convert_docx_to_markdown.py --docx_file $FILE_NAME.docx --md_file $FILE_NAME.md
