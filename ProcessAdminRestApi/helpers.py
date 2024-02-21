from io import BytesIO

import pandas as pd
from django.core.files.storage import default_storage
from pandas.api.types import is_datetime64_any_dtype as is_datetime

from ProcessAdminRestApi.models.fields.XLSX_field import XLSXField


def convert_dfs_in_excel(path, data_frames, sheet_names=None, merge_cells=False, formats={}, index=True):
    """
    :param path: string to storage location of xlsx file
    :param data_frames: list of dataframes that will be inserted into an Excel tab each
    :param sheet_names: list of sheet names corresponding to the data_frames
    :rtype: None
    """
    if sheet_names is None:
        sheet_names = ['Sheet']
    excel_file = BytesIO()
    writer = pd.ExcelWriter(excel_file, engine='xlsxwriter')
    df: pd.DataFrame
    for df, sheet_name in zip(data_frames, sheet_names):
        if df is not None:
            if index:
                idx_length = df.index.nlevels
            else:
                idx_length = 0
            df.to_excel(writer, sheet_name=sheet_name, merge_cells=merge_cells, freeze_panes=(1, idx_length), index=index)

            worksheet = writer.sheets[sheet_name]  # pull worksheet object
            cell_formats = {}
            for format in formats:
                cell_formats[format] = writer.book.add_format({'num_format': formats[format]})
            if index:
                index_frame = df.index.to_frame()
                for idx, col in enumerate(index_frame):  # loop through all columns
                    series = index_frame[col]
                    max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 1  # adding a little extra space
                    if is_datetime(series):
                        max_len = 22
                    worksheet.set_column(idx, idx, max_len)  # set column width

            for idx, col in enumerate(df):  # loop through all columns
                series = df[col]
                max_len = max((
                    series.astype(str).map(len).max(), len(str(series.name)))) + 1  # adding a little extra space
                worksheet.set_column(idx + idx_length, idx + idx_length, max_len)  # set column width
                # set Cell format
                if col in formats:
                    worksheet.set_column(idx + idx_length, idx + idx_length, max_len, cell_format=cell_formats[col])
                elif is_datetime(df[col]):
                    pass
                else:
                    worksheet.set_column(idx + idx_length, idx + idx_length, max_len, cell_format=writer.book.add_format({'num_format': XLSXField.cell_format}))
            # Add autofilter:
            worksheet.autofilter(0, 0, len(df), idx_length + len(df.columns))

    writer.save()
    writer.close()

    # Extract the Excel file contents from BytesIO
    excel_file_contents = excel_file.getvalue()

    # Save the Excel file contents to the specified path
    with default_storage.open(path, 'wb') as output_excel_file:
        output_excel_file.write(excel_file_contents)
