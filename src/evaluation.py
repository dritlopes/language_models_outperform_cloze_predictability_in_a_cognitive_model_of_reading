import pandas as pd
import numpy as np
from collections import defaultdict
import statsmodels.api as sm
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sb
from utils import get_pred_dict, get_word_freq, pre_process_string
import math
import os

# ---------------- Simulation eye-movement measures ------------------
def get_first_pass_fixations(simulation_df:pd.DataFrame):

    """
    Gather first-pass fixation to determine word-measures that are based on first-pass fixations, e.g. skipping, first fixation, single fixation and gaze duration.
    First-pass fixations of a word are defined as the first fixation on that word resulted from a forward or wordskip saccade, plus all sequential refixations.
    :param simulation_output: contains the fixations of the model simulation(s)
    :return: a pandas dataframe with only the fixations belonging to first-pass
    """

    first_pass_indices = []

    for sim_id, sim_hist in simulation_df.groupby('simulation_id'):
        for text_id, text_hist in sim_hist.groupby('text_id'):
            for word, fix_hist in text_hist.groupby('word_id'):
                # make sure the eyes have NOT moved to beyond the word before fixating it for the first time
                if all(word > previous_word for previous_word in
                       text_hist['word_id'].tolist()[:fix_hist['fixation_counter'].tolist()[0] - 1]):
                    # check each fixation on the word
                    for i, fix in fix_hist.iterrows():
                        # if fixation was not the result of a regression
                        if fix['saccade type'] != 'regression':
                            # add to first-pass if first fixation on word
                            if fix['fixation_counter'] == fix_hist['fixation_counter'].tolist()[0]:
                                first_pass_indices.append(i)
                            # add to first-pass the following fixations which are sequential to first fixation
                            elif i == first_pass_indices[-1] + 1:
                                first_pass_indices.append(i)

    first_pass = simulation_df.filter(items=first_pass_indices, axis=0)
    # first_pass.to_csv('../results/first_pass.csv')

    return first_pass

def get_text_words(stimuli):

    words_in_text = defaultdict(list)
    for word_info, rows in stimuli.groupby(['text_id', 'word_id']):
        words_in_text[int(word_info[0])].append(rows['word'].tolist()[0])
    return words_in_text

def get_skipped_words(first_pass:pd.DataFrame, words_in_text:defaultdict):

    """
    For each simulation, compare token ids in first pass with token ids from specific text. The token indicices not in first pass are considered skipped
    :param first_pass: pandas dataframe containing fixations in first-pass
    :param words_in_text: list of words in text
    :return: pandas dataframe with only words skipped by in at least one simulation
    """
    skipped_words = defaultdict(list)

    for sim_id, sim_hist in first_pass.groupby('simulation_id'):
        for text_id, text_hist in sim_hist.groupby('text_id'):
            for word_id, word in enumerate(words_in_text[text_id], 1):
                skipped_words['simulation_id'].append(sim_id)
                skipped_words['text_id'].append(text_id)
                skipped_words['word_id'].append(word_id)
                skipped_words['word'].append(word)
                if word_id not in list(text_hist['word_id'].unique()):
                    skipped_words['skip'].append(1)
                else:
                    skipped_words['skip'].append(0)

    skipped_added = pd.DataFrame.from_dict(skipped_words)

    return skipped_added

def get_single_fix_words(first_pass):

    single_fix = defaultdict(list)

    for word_info, hist in first_pass.groupby(['simulation_id', 'text_id', 'word_id']):
        single_fix['simulation_id'].append(word_info[0])
        single_fix['text_id'].append(word_info[1])
        single_fix['word_id'].append(word_info[2])
        if len(hist) == 1:
            single_fix['single_fix'].append(1)
        else:
            single_fix['single_fix'].append(0)

    single_fix = pd.DataFrame.from_dict(single_fix)

    return single_fix

def aggregate_fixations_per_word(simulation_output, first_pass, stimuli, measures):

    """
    Transform fixation data into word-centred data, where each row is a word in each text/trial in each simulation.
    Add columns with word-level eye movement measures
    :param simulation_output:
    :param first_pass:
    :param stimuli:
    :param measures:
    :return: dataframe with fixations aggregated per word per simulation
    """

    results_per_word = dict()

    for measure in measures:

        if measure == 'skip':
            results_per_word['skip'] = get_skipped_words(first_pass, get_text_words(stimuli))

        elif measure == 'single_fix':
            results_per_word['single_fix'] = get_single_fix_words(first_pass)

        elif measure == 'first_fix_duration':
            results_per_word['first_fix_duration'] = first_pass.loc[first_pass.groupby(
                ['simulation_id', 'text_id', 'word_id']).apply(lambda x: x.index[0]).values, :].reset_index().rename(
                columns={'fixation duration': 'first_fix_duration'})

        elif measure == 'gaze_duration':
            results_per_word['gaze_duration'] = first_pass.groupby(['simulation_id', 'text_id', 'word_id'])[
                ['fixation duration']].sum().reset_index().rename(columns={'fixation duration': 'gaze_duration'})

        elif measure == 'total_reading_time':
            results_per_word['total_reading_time'] = simulation_output.groupby(['simulation_id', 'text_id', 'word_id'])[
                ['fixation duration']].sum().reset_index().rename(columns={'fixation duration': 'total_reading_time'})

    # merge all
    result_columns = defaultdict(list)
    for item, hist in stimuli.groupby(['text_id', 'word_id']):
        for simulation_id in simulation_output['simulation_id'].unique():
            result_columns['simulation_id'].append(simulation_id)
            result_columns['text_id'].append(item[0])
            result_columns['word_id'].append(item[1])
            result_columns['word'].append(hist['word'].tolist()[0])
            for measure in results_per_word.keys():
                measure_value = np.nan
                item_info = f"simulation_id=={simulation_id} & text_id=={item[0]} & word_id=={item[1]}"
                cell = results_per_word[measure].query(item_info)[measure]
                if len(cell) > 0: measure_value = cell.item()
                result_columns[measure].append(measure_value)

    results = pd.DataFrame(result_columns)

    return results

def pre_process_eye_tracking(eye_tracking: pd.DataFrame, eye_tracking_filepath: str):

    if 'provo' in eye_tracking_filepath.lower():
        # make sure all columns of interest are named as code expects

        eye_tracking = eye_tracking.rename(columns={'Word_Unique_ID': 'id',
                                                     'Text_ID': 'text_id',
                                                     'Word_Number': 'word_id',
                                                     'Participant_ID': 'participant_id',
                                                     'Word': 'word',
                                                     'IA_SKIP': 'skip',
                                                     'IA_FIRST_FIXATION_DURATION': 'first_fix_duration',
                                                     'IA_FIRST_RUN_DWELL_TIME': 'gaze_duration',
                                                     'IA_DWELL_TIME': 'total_reading_time'})

        # remove rows where Word_Number is nan value, to be able to convert floats to ints
        eye_tracking = eye_tracking.dropna(subset=['word_id'])

        # - 1 to be compatible with index used in simulation (starting from 0, instead of 1)
        eye_tracking['word_id'] = eye_tracking['word_id'].astype(int).apply(lambda x: x - 1)
        eye_tracking['text_id'] = eye_tracking['text_id'].apply(lambda x: x - 1)

        # fix some errors in provo eye_tracking data
        eye_tracking.loc[(eye_tracking['word_id'] == 2) & (eye_tracking['word'] == 'evolution') & (eye_tracking['text_id'] == 17), 'word_id'] = 51

        # add single fix
        single_fix = []
        # determine which words were fixated only once by each participant
        for word, hist in eye_tracking.groupby(['participant_id', 'text_id', 'word_id']):
            # single fix is defined as: if gaze duration equals first fixation duration,
            # then word was fixated only once in first pass
            assert len(hist) == 1, print(word, hist)
            if hist['gaze_duration'].tolist()[0] == hist['first_fix_duration'].tolist()[0]:
                single_fix.append(1)
            else:
                single_fix.append(0)
        # add binary single fix column
        eye_tracking['single_fix'] = single_fix

        # add item level id (word id per participant)
        item_id = []
        for participant, hist in eye_tracking.groupby('participant_id'):
            item_counter = 0
            for info, rows in hist.groupby(['text_id', 'word_id']):
                item_id.append(item_counter)
                item_counter += 1
        eye_tracking['id'] = item_id

    # make sure words look like words in simulation (lowercased, without punctuation, etc)
    eye_tracking['word'] = [pre_process_string(word) for word in eye_tracking['word']]

    return eye_tracking

def get_word_factors(pm, eye_movements_df, factors):

    if 'predictability' in factors:
        pred_map = get_pred_dict(pm,None)
        pred_column = []
        for i, item in eye_movements_df.iterrows():
            pred_value = 0.0
            if str(item['text_id']) in pred_map.keys():
                if str(item['word_id']) in pred_map[str(item['text_id'])].keys():
                    word = item['word'].strip()
                    if word in pred_map[str(item['text_id'])][str(item['word_id'])].keys():
                        pred_value = pred_map[str(item['text_id'])][str(item['word_id'])][word]
            pred_column.append(pred_value)
        eye_movements_df['predictability'] = pred_column

    if 'frequency' in factors:
        freq_map = get_word_freq(pm,None)
        freq_column = []
        for i, item in eye_movements_df.iterrows():
            freq_value = 0.0
            word = item['word'].strip()
            if word in freq_map.keys():
                freq_value = freq_map[word]
            freq_column.append(freq_value)
        eye_movements_df['frequency'] = freq_column

    if 'length' in factors:
        length_column = []
        for i, item in eye_movements_df.iterrows():
            word = item['word'].strip()
            length_column.append(len(word))
        eye_movements_df['length'] = length_column

    return eye_movements_df

def drop_nan_values(true_values:pd.Series, simulated_values:pd.Series):

    values = defaultdict(list)
    counter = 0
    for true_value, simulated_value in zip(true_values, simulated_values):
        if not true_values.isnull()[counter] and not simulated_values.isnull()[counter]:
            values['true'].append(true_value)
            values['pred'].append(simulated_value)
        counter += 1
    return values

# ---------------- Evaluation functions ------------------
def compute_root_mean_squared_error(true_values:list, simulated_values:list):

    # root mean squared error measures the average difference between values predicted by the model
    # and the eye-tracking values. It provides an estimate of how well the model was able to predict the
    # eye-tracking value.
    return math.sqrt(np.square(np.subtract(simulated_values, true_values)).mean())

def compute_error(measures, true, pred):

    mean2errors = defaultdict(list)

    for measure in measures:
        # excluding words with nan value, e.g. skipped words of prob 1. Should words that are always skipped be included in the equation?
        values = drop_nan_values(true[measure], pred[measure])
        mean2error = compute_root_mean_squared_error(values['true'], values['pred'])
        mean2errors['eye_tracking_measure'].append(measure)
        mean2errors['mean_squared_error'].append(mean2error)
    mean2error_df = pd.DataFrame(mean2errors)

    return mean2error_df

def fit_mixed_effects(parameters, true, predicted, output_filepath):
    
    # generalized mixed effects model doc: https://www.statsmodels.org/stable/generated/statsmodels.genmod.bayes_mixed_glm.BinomialBayesMixedGLM.from_formula.html#statsmodels.genmod.bayes_mixed_glm.BinomialBayesMixedGLM.from_formula
    # linear mixed effects doc: https://www.statsmodels.org/stable/generated/statsmodels.regression.mixed_linear_model.MixedLM.from_formula.html

    # linear mixed effects models to determine if the simulation data can predict the human data
    for measure in parameters.evaluation_measures:
        # merge pred and true
        # makes sure predicted means are repeated for each participant in human data
        predicted_measure = []
        for item, hist in true.groupby(['participant_id','text_id','word_id']):
            pred_value = predicted.query(f"text_id=={item[1]} & word_id=={item[2]}")[measure]
            predicted_measure.append(pred_value.item())
        true[f'simulated_{measure}'] = predicted_measure
        data_measure = true[['participant_id', 'id', 'text_id', 'word_id', measure, f'simulated_{measure}']]
        # drop nan values as statsmodels cannot handle nan values and throws error in case there is any
        data_measure = data_measure.dropna()
        # in case of binary dependent variable (eye-movement measure)
        if {int(value) for value in data_measure[measure].unique()} == {1, 0}:
            random = {"participant_id": "0+C(participant_id)",
                       "id": "0+C(id)"}
            stats_model = sm.BinomialBayesMixedGLM.from_formula(f"{measure} ~ simulated_{measure}",
                                                                vc_formulas=random,
                                                                data=data_measure)
            stats_result = stats_model.fit_map(method='BFGS')
            print(stats_result.summary())
            # stats_result.save(output_filepath.replace('simulation_', f'glm_{measure}_').replace('.csv', '.pkl'))
            with open(output_filepath.replace('simulation_', f'glm_{measure}_').replace('.csv', '.txt'), 'w') as fh:
                fh.write(stats_result.summary().as_text())
        else:
            # stats_model = smf.mixedlm(f"{measure} ~ simulated_{measure}",data_measure,groups=data_measure['participant_id'])
            # from statsmodel doc: To include crossed random effects in a model,
            # it is necessary to treat the entire dataset as a single group.
            # The variance components arguments to the model can then be used to define models
            # with various combinations of crossed and non-crossed random effects.
            data_measure["group"] = 1
            # add independent random intercept for each vc_formula key
            random = {"participant_id": "0+C(participant_id)",
                       "id": "0+C(id)"}
            stats_model = sm.MixedLM.from_formula(f"{measure} ~ simulated_{measure}",
                                                  groups="group",
                                                  vc_formula=random,
                                                  data=data_measure)
            # stats_model = sm.MixedLM.from_formula(f"{measure} ~ simulated_{measure}",
            #                                       groups='participant_id',
            #                                       re_formula="1",
            #                                       vc_formula={"text_id":"0+C(text_id)",
            #                                                   "word_id":"0+C(word_id)"},
            #                                       data=data_measure)
            stats_result = stats_model.fit(method=["lbfgs"])
            print(stats_result.summary())
           #  stats_result.save(output_filepath.replace('simulation_', f'lm_{measure}_').replace('.csv','.pkl'))
            with open(output_filepath.replace('simulation_', f'lm_{measure}_').replace('.csv', '.txt'), 'w') as fh:
                fh.write(stats_result.summary().as_text())

def scale_human_durations(data_log, parameters_list):

    all_measures = [measure for parameters in parameters_list for measure in parameters.evaluation_measures]
    for data_name, data in data_log.items():
        if 'eye_tracking' in data_name.lower():
            for measure in all_measures:
                if measure in ['total_reading_time', 'first_fixation_duration', 'gaze_duration']:
                    # check how many ob1 reading cycles the duration corresponds and multiply the number of cycles with 25
                    data[measure] = data[measure].apply(lambda x: int(x / 25) * 25 if not np.isnan(x) else x)
    return data_log

def merge_human_and_simulation_data(data_log, parameters_list):

    all_data = []
    for data_name, data in data_log.items():
        if data_name == parameters_list[0].eye_tracking_filepath + '_mean':
            if 'provo' in data_name.lower():
                data["predictor"] = ['PROVO' for i in range(len(data))]
                data['id'] = [i for i in range(len(data))]
                all_data.append(data)
        elif 'language model' in data_name.lower() and '_mean' in data_name.lower():
            data["predictor"] = ['language model' for i in range(len(data))]
            data['id'] = [i for i in range(len(data))]
            all_data.append(data)
        elif 'cloze' in data_name.lower() and '_mean' in data_name.lower():
            data['predictor'] = ['cloze' for i in range(len(data))]
            data['id'] = [i for i in range(len(data))]
            all_data.append(data)
    data = pd.concat(all_data, axis=0).reset_index()

    return data

def plot_fixed_factor_vs_eye_movement(data, fixed_factors, measures, results_filepath):

    results_dir = os.path.dirname(results_filepath)
    for fixed_factor in fixed_factors:
        for measure in measures:
            plot = sb.relplot(data=data, x=measure, y=fixed_factor, hue='predictor', kind='line')
            filepath = f"{results_dir}/plot_{fixed_factor}_{measure}.png"
            plot.figure.savefig(filepath)

def plot_word_measures(data, measures, results_filepath):

    results_dir = os.path.dirname(results_filepath)
    for measure in measures:
        # plot item level mean
        data['id'] = data['id'].apply(lambda x: str(x))
        plot = sb.relplot(data=data, x='id', y=measure, hue='predictor', kind='scatter')
        filepath = f"{results_dir}/plot_item_{measure}.png"
        plot.figure.savefig(filepath)
        # plot experiment level mean
        # data_mean = data[['predictor',measure]].groupby('predictor').mean().reset_index()
        plot = sb.barplot(data=data, x="predictor", y=measure)
        filepath = f"{results_dir}/plot_{measure}.png"
        plot.figure.savefig(filepath)

# ---------------- MAIN ------------------
def evaluate_output (parameters_list: list):

    # register which human and simulated data have been analysed
    data_log = dict()

    print(f'\nEvaluating outputs...')

    # makes sure more than one experiment can be evaluated at once
    for parameters in parameters_list:

        if parameters.task_to_run == 'continuous reading':

            output_filepath = parameters.results_filepath
            simulation_output = pd.read_csv(output_filepath, sep='\t')
            simulation_output = simulation_output.rename(columns={'foveal word index': 'word_id',
                                                                  'foveal word': 'word'})

            if 'provo' in parameters.eye_tracking_filepath.lower():
                # exclude first word of every passage (not in eye tracking -PROVO- data either)
                simulation_output = simulation_output[simulation_output['word_id'] != 0]

            # get word-level eye-movement measures in human data
            if parameters.eye_tracking_filepath in data_log.keys():
                true_eye_movements = data_log[parameters.eye_tracking_filepath]
                mean_true_eye_movements = data_log[parameters.eye_tracking_filepath + '_mean']
            else:
                # read in eye_tracking data for comparing simulation with observed measures
                # encoding = chardet.detect(open(parameters.eye_tracking_filepath, "rb").read())['encoding']
                eye_tracking = pd.read_csv(parameters.eye_tracking_filepath, encoding="ISO-8859-1")
                # pre-process eye-tracking data to the format needed
                true_eye_movements = pre_process_eye_tracking(eye_tracking, parameters.eye_tracking_filepath)
                # only including first two texts for now
                true_eye_movements = true_eye_movements[true_eye_movements['text_id'] < 2]
                # get word factors (e.g. frequency, length, predictability)
                true_eye_movements = get_word_factors(parameters, true_eye_movements, parameters.fixed_factors)
                # save out pre-processed data
                filepath = parameters.eye_tracking_filepath.replace('-Eyetracking_Data', '_eye_tracking')
                true_eye_movements.to_csv(filepath, sep='\t')
                data_log[parameters.eye_tracking_filepath] = true_eye_movements
                # get word level measures from eye_tracking, averaged over participants
                mean_true_eye_movements = true_eye_movements.groupby(['text_id', 'word_id', 'word'])\
                    [parameters.evaluation_measures].mean().reset_index()
                mean_true_eye_movements = get_word_factors(parameters, mean_true_eye_movements, parameters.fixed_factors)
                # save out averaged data
                filepath = parameters.eye_tracking_filepath.replace('-Eyetracking_Data', '_eye_tracking_mean')
                mean_true_eye_movements.to_csv(filepath, sep='\t', index_label='id')
                data_log[parameters.eye_tracking_filepath + '_mean'] = mean_true_eye_movements

            # get word-level eye-movement measures in simulation data
            stimuli = mean_true_eye_movements[['text_id', 'word_id', 'word']]
            # first aggregate fixations per word, keeping simulation level
            predicted_eye_movements = aggregate_fixations_per_word(simulation_output,
                                                                   get_first_pass_fixations(simulation_output),
                                                                   stimuli,
                                                                   parameters.evaluation_measures)
            # get word factors (e.g. frequency, length, predictability)
            predicted_eye_movements = get_word_factors(parameters, predicted_eye_movements, parameters.fixed_factors)
            filepath = output_filepath.replace('simulation_', f'simulation_eye_movements_')
            predicted_eye_movements.to_csv(filepath, sep='\t', index_label='id')
            data_log[parameters.results_filepath] = predicted_eye_movements
            # then average over simulations to get the means
            mean_predicted_eye_movements = predicted_eye_movements.groupby(['text_id', 'word_id', 'word'])\
                [parameters.evaluation_measures].mean().reset_index()
            mean_predicted_eye_movements = get_word_factors(parameters, mean_predicted_eye_movements, parameters.fixed_factors)
            filepath = output_filepath.replace('simulation_', f'simulation_eye_movements_mean_')
            mean_predicted_eye_movements.to_csv(filepath, sep='\t', index_label='id')
            data_log[parameters.results_filepath + '_mean'] = mean_predicted_eye_movements

            # mean square error between each measure in simulation and eye-tracking
            mean2error_df = compute_error(parameters.evaluation_measures,
                                          mean_true_eye_movements,
                                          mean_predicted_eye_movements)
            filepath = output_filepath.replace('simulation_', f'RM2E_eye_movements_')
            mean2error_df.to_csv(filepath, sep='\t', index=False)

            # stat tests
            # fit_mixed_effects(parameters, true_eye_movements, mean_predicted_eye_movements, output_filepath)

    # scale durations from eye-tracking data to be more aligned to OB1 durations which happens in cycles of 25ms
    data_log = scale_human_durations(data_log, parameters_list)

    # merge simulation and human measures
    all_data = merge_human_and_simulation_data(data_log, parameters_list)

    # plot results
    plot_fixed_factor_vs_eye_movement(all_data,
                                      ['predictability'],
                                      parameters_list[0].evaluation_measures,
                                      parameters_list[0].results_filepath)
    plot_word_measures(all_data,
                       parameters_list[0].evaluation_measures,
                       parameters_list[0].results_filepath)




