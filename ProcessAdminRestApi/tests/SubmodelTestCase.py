from enum import Enum

import pandas as pd

from datetime import datetime
from secrets import randbelow


class TestType(Enum):
    EXACT = 'Exact'
    DUPLICATE = 'Duplicate'
    RANDOM = 'Random'
    SUM = 'Sum'


def compare_dfs(df_list, dic, column_names_check=False, format_check=False):
    # df_list should include the two dataframes to be compared, data type: List of dataframes
    # dic should include the comparisons to be made, data type: Dictionary of list of strings
    # column_names_check (optional): Defines whether the column names of both dfs should be compared, data type: Boolean
    # format_check (optional): Defines whether the data types of columns of both dfs should be compared, data type: Boolean

    # Step 1: create dfs from list and empty result df
    df1 = df_list[0]
    df2 = df_list[1]
    # Step 2: Check number of entries
    check_number_of_lines(df1, df2)

    # Step 3: Compare values according to dic
    for col_name in dic:
        test_definition = dic[col_name]
        if col_name in df1.columns and col_name in df2.columns:
            accuracy = None
            grouped_by = None

            # String passed
            if isinstance(test_definition, TestType):
                test_type = test_definition
                check_values(col_name, df1, df2, test_type, accuracy, grouped_by)

            # Dictionary passed
            if isinstance(test_definition, dict):
                if "accuracy" in test_definition:
                    accuracy = test_definition['accuracy']
                    accuracy = len(accuracy.split(",")[1])
                else:
                    accuracy = None
                if "grouped_by" in test_definition:
                    grouped_by = test_definition['grouped_by']
                else:
                    grouped_by = None
                test_type = test_definition['method']
                check_values(col_name, df1, df2, test_type, accuracy, grouped_by)

            # List passed
            if isinstance(test_definition, list):
                list_test_definitions = test_definition
                for test_definition in list_test_definitions:
                    accuracy = None
                    grouped_by = None
                    test_type = None
                    # String in List
                    if isinstance(test_definition, TestType):
                        test_type = test_definition
                    # Dictionary in List
                    if isinstance(test_definition, dict):
                        if "accuracy" in test_definition:
                            accuracy = test_definition['accuracy']
                            accuracy = len(accuracy.split(",")[1])
                        else:
                            accuracy = None
                        if "grouped_by" in test_definition:
                            grouped_by = test_definition['grouped_by']
                        else:
                            grouped_by = None
                        test_type = test_definition['method']
                    check_values(col_name, df1, df2, test_type, accuracy, grouped_by)
        else:
            print(
                f'Can not compare the values in column {col_name} because it is missing in one of the two DataFrames.')

    # Step 4: Check names of columns (optional)
    if column_names_check:
        for column in df1.columns:
            if column not in df2.columns:
                print(f'WARNING: {column}, which is in DataFrame 1 is not in DataFrame 2!')
        for column in df2.columns:
            if column not in df1.columns:
                print(f'WARNING: {column}, which is in DataFrame 2 is not in DataFrame 1!')

    # Step 5: Check format (optional)
    if format_check:
        check_format(df1, df2)


def check_number_of_lines(df1, df2):
    rows_df1 = len(df1.axes[0])
    rows_df2 = len(df2.axes[0])
    if rows_df1 == rows_df2:
        print('Both DataFrames have the same number of entries.')
    else:
        print('The DataFrames have a different number of entries!')


def get_dtypes_in_column(series):
    dtypes_list = []
    for entry in series:
        if isinstance(entry, float):
            dtypes_list.append('Float')
        elif isinstance(entry, str):
            dtypes_list.append('String')
        elif isinstance(entry, datetime):
            dtypes_list.append('Date')
        elif isinstance(entry, int):
            dtypes_list.append('Integer')
    are_identical = all(element == dtypes_list[0] for element in dtypes_list)
    if are_identical:
        return dtypes_list[0]
    else:
        return 'inconsistent typed'


def check_values_test(df1, df2, col_name, accuracy, action):
    series_df1 = df1[col_name]
    series_df2 = df2[col_name]
    dtype_series_df1 = get_dtypes_in_column(series_df1)
    dtype_series_df2 = get_dtypes_in_column(series_df2)

    if action == TestType.EXACT:
        exact_test_successful = True
        for ent in series_df1.items():
            index = ent[0]
            val_df1 = ent[1]
            if index in list(df2.index):
                val_df2 = series_df2[index]
                if accuracy is not None and isinstance(val_df1, float) and isinstance(val_df2, float):
                    val_df1 = round(val_df1, accuracy)
                    val_df2 = round(val_df2, accuracy)
                if val_df1 != val_df2:
                    exact_test_successful = False
                    print(f'{col_name} - Values are not equal for entry with index {index} for column {col_name}! {val_df1} in DataFrame 1 and {val_df2} in DataFrame 2.')
            else:
                exact_test_successful = False
                print(
                    f'{col_name} - Index {index} does not exist in Dataframe 2')
        if exact_test_successful:
            print(f'{col_name} - Exact Test was successful.')
        else:
            print(f'{col_name} - Exact Test failed.')

    elif action == TestType.SUM:
        if dtype_series_df1 == 'Float' and dtype_series_df2 == 'Float':
            sum_df1 = series_df1.sum()
            sum_df2 = series_df2.sum()
            if accuracy is not None and isinstance(sum_df1, float) and isinstance(sum_df2, float):
                sum_df1 = round(sum_df1, accuracy)
                sum_df2 = round(sum_df2, accuracy)
            if sum_df1 == sum_df2:
                print(f'{col_name} - Checksum correct! - {sum_df1}')
            else:
                print(f'{col_name} - Checksum not correct for column {col_name}! - DF1: {sum_df1}; DF2: {sum_df2}')
        else:
            print(f'{col_name} - WARNING: You can not sum up a column of {dtype_series_df1} values.')

    elif action == TestType.RANDOM:
        ran = len(series_df1)
        for i in range(0, 5):
            row_number = randbelow(ran)
            index = df1.index[row_number]
            val_df1 = df1.loc[index][col_name]

            if index in list(df2.index):
                val_df2 = df2.loc[index][col_name]
                if accuracy is not None and isinstance(val_df1, float) and isinstance(val_df2, float):
                    val_df1 = round(val_df1, accuracy)
                    val_df2 = round(val_df2, accuracy)
                if val_df1 == val_df2:
                    print(
                        f'{col_name} - Random value check {i + 1} of 5 for index {index} completed: Compared values are equal.')
                else:
                    print(
                        f'{col_name} - Random value check {i + 1} of 5 for index {index} completed: Compared values are not equal.')
            else:
                print(f'{col_name} - Random value check {i + 1} of 5 for index {index} completed: Index not found in Dataframe 2.')

    elif action == TestType.DUPLICATE:
        duplicates_df1 = df1[df1.duplicated(subset=[col_name], keep=False)]
        duplicates_df2 = df2[df2.duplicated(subset=[col_name], keep=False)]
        if duplicates_df1.empty:
            print(f'DF1 - {col_name} - No duplicates.')
        else:
            for index, row in duplicates_df1.iterrows():
                print(f'DF1 - {col_name} - Value: {row[col_name]} is duplicated. Index: {index}')
        if duplicates_df2.empty:
            print(f'DF2 - {col_name} - No duplicates.')
        else:
            for index, row in duplicates_df2.iterrows():
                print(f'DF2 - {col_name} - Value: {row[col_name]} is duplicated. Index: {index}')


def check_values(col_name, df1, df2, action, accuracy=None, grouped_by=None):
    if grouped_by:
        distinct_values = df1[grouped_by].unique()
        for val in distinct_values:
            df1_new = df1[df1[grouped_by] == val]
            df2_new = df2[df2[grouped_by] == val]
            if len(df1_new) > 1 and len(df2_new) > 1:
                check_values_test(df1_new, df2_new, col_name, accuracy, action)
            else:
                pass
    else:
        check_values_test(df1, df2, col_name, accuracy, action)


def check_format(df1, df2):
    count_total = 0
    count_errors = 0
    for column in df1.columns:
        if column in df2.columns:
            count_total += 1
            if isinstance(df1[column][0], str):
                type_df1 = 'String'
            elif isinstance(df1[column][0], datetime):
                type_df1 = 'Datetime'
            elif isinstance(df1[column][0], float):
                type_df1 = 'Float'
            else:
                type_df1 = 'None'

            if isinstance(df2[column][0], str):
                type_df2 = 'String'
            elif isinstance(df2[column][0], datetime):
                type_df2 = 'Datetime'
            elif isinstance(df2[column][0], float):
                type_df2 = 'Float'
            else:
                type_df2 = 'None'

            if type_df1 != type_df2:
                print(f'Data type different for {column}!')
                count_errors += 1
        else:
            print(f'{column} - Column {column} is not in both DataFrames, can not compare data type.')

    print(f'Format Check: {count_total - count_errors} of {count_total} column checks successful.')
