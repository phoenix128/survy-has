import copy
import re

from survy.core.app import App


class Utils:
    @classmethod
    def replace_variables_text(cls, format_text, params, add_global=True):
        if params is None:
            params = {}

        if add_global:
            p = copy.deepcopy(params)
            params = copy.deepcopy(App.get_variables())
            params.update(p)

        for k, v in params.items():
            format_text = format_text.replace('%' + k + '%', v)

        return format_text

    @classmethod
    def replace_variables_dict(cls, format_dict, params=None, add_global=True):
        if params is None:
            params = {}

        if add_global:
            p = copy.deepcopy(params)
            params = copy.deepcopy(App.get_variables())
            params.update(p)

        out = copy.deepcopy(format_dict)
        for key, value in format_dict.items():
            if isinstance(value, list):
                for i in range(0, len(value)):
                    if isinstance(value[i], str):
                        variables = re.findall(r'%([\w\-_]+?)%', value[i])

                        for variable in variables:
                            if variable in params:
                                out[key][i] = out[key][i].replace('%' + variable + '%', params[variable])

            else:
                if isinstance(value, str):
                    variables = re.findall(r'%([\w\-_]+?)%', value)

                    for variable in variables:
                        if variable in params:
                            out[key] = out[key].replace('%' + variable + '%', params[variable])

        return out

    @classmethod
    def complex_match(cls, check_type, check_value, value):
        """
        Perform a complex match and return a dict of objects for regex or False on failure
        :param check_type:
        :param check_value:
        :param value:
        :return:
        """
        if isinstance(check_value, list):
            out = {}
            for cv in check_value:
                res = cls.complex_match(
                    check_type=check_type,
                    check_value=cv,
                    value=value
                )

                if res is False:
                    return False

                if isinstance(res, dict):
                    out.update(res)

            return out

        if check_type == 'contains':
            return value in check_value

        if check_type == 'icontains':
            return value.lower() in check_value.lower()

        if check_type == 'eq':
            return str(value) == str(check_value)

        if check_type == 'neq':
            return str(value) != str(check_value)

        if check_type == 'ineq':
            return str(value).lower() != str(check_value).lower()

        if check_type == 'gt':
            return int(value) > int(check_value)

        if check_type == 'lt':
            return int(value) < int(check_value)

        if check_type == 'gteq':
            return int(value) <= int(check_value)

        if check_type == 'lteq':
            return int(value) >= int(check_value)

        if check_type == 'regex':
            m = re.search(check_value, str(value))
            if not m:
                return False
            return m.groupdict()

        if check_type == 'iregex':
            m = re.search(check_value, str(value), flags=re.IGNORECASE)
            if not m:
                return False
            return m.groupdict()

        # check_type == 'ieq'
        return str(check_value).lower() == str(value).lower()
