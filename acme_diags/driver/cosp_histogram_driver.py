from __future__ import print_function

import os
import sys
import cdms2
import acme_diags
from acme_diags.plot import plot
from acme_diags.derivations import acme
from acme_diags.metrics import rmse, corr, min_cdms, max_cdms, mean
from acme_diags.driver import utils


def create_metrics(ref, test, ref_regrid, test_regrid, diff):
    """Creates the mean, max, min, rmse, corr in a dictionary"""
    metrics_dict = {}
    metrics_dict['ref'] = {
        'min': min_cdms(ref),
        'max': max_cdms(ref),
        'mean': mean(ref)
    }
    metrics_dict['test'] = {
        'min': min_cdms(test),
        'max': max_cdms(test),
        'mean': mean(test)
    }

    metrics_dict['diff'] = {
        'min': min_cdms(diff),
        'max': max_cdms(diff),
        'mean': mean(diff)
    }
    metrics_dict['misc'] = {
        'rmse': rmse(test_regrid, ref_regrid),
        'corr': corr(test_regrid, ref_regrid)
    }

    return metrics_dict


def run_diag(parameter):
    parameter.reference_data_path
    parameter.test_data_path

    variables = parameter.variables
    seasons = parameter.seasons
    ref_name = parameter.ref_name
    regions = parameter.regions

    for season in seasons:
        try:
            filename1 = utils.get_test_filename(parameter, season)
            filename2 = utils.get_ref_filename(parameter, season)
        except IOError as e:
            print(e)
            # the file for the current parameters wasn't found, move to next
            # parameters
            continue

        print('test file: {}'.format(filename1))
        print('reference file: {}'.format(filename2))

        f_mod = cdms2.open(filename1)
        f_obs = cdms2.open(filename2)

        if parameter.short_test_name:
            parameter.test_name_yrs = parameter.short_test_name
        else:
            parameter.test_name_yrs = parameter.test_name

        try:
            yrs_averaged =  f_mod.getglobal('yrs_averaged')
            parameter.test_name_yrs = parameter.test_name_yrs + ' (' + yrs_averaged +')'

        except:
            print('No yrs_averaged exists in global attributes')
            parameter.test_name_yrs = parameter.test_name_yrs

        # save land/ocean fraction for masking
        try:
            land_frac = f_mod('LANDFRAC')
            ocean_frac = f_mod('OCNFRAC')
        except BaseException:
            mask_path = os.path.join(acme_diags.INSTALL_PATH, 'acme_ne30_ocean_land_mask.nc')
            f0 = cdms2.open(mask_path)
            land_frac = f0('LANDFRAC')
            ocean_frac = f0('OCNFRAC')
            f0.close()

        for var in variables:
            print('Variable: {}'.format(var))
            parameter.var_id = var
            mv1 = acme.process_derived_var(
                var, acme.derived_variables, f_mod, parameter)
            mv2 = acme.process_derived_var(
                var, acme.derived_variables, f_obs, parameter)

            parameter.viewer_descr[var] = mv1.long_name if hasattr(
                mv1, 'long_name') else 'No long_name attr in test data.'

            # select region
            if len(regions) == 0:
                regions = ['global']

            for region in regions:
                print("Selected region: {}".format(region))

                mv1_domain, mv2_domain = utils.select_region(
                    region, mv1, mv2, land_frac, ocean_frac, parameter)

                parameter.output_file = '-'.join(
                    [ref_name, var, season, region])
                parameter.main_title = str(' '.join([var, season, region]))

                mv1_domain_mean = mean(mv1_domain)
                mv2_domain_mean = mean(mv2_domain)

                diff = mv1_domain_mean - mv2_domain_mean
                mv1_domain_mean.id = var
                mv2_domain_mean.id = var
                diff.id = var
                parameter.backend = 'cartopy'
                plot(parameter.current_set, mv2_domain_mean,
                     mv1_domain_mean, diff, {}, parameter)
#                    plot(parameter.current_set, mv2_domain, mv1_domain, diff, metrics_dict, parameter)
#                    utils.save_ncfiles(parameter.current_set, mv1_domain, mv2_domain, diff, parameter)

        f_obs.close()
        f_mod.close()
    return parameter
