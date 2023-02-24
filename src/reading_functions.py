import numpy as np
import pickle
import os
import math
import re

def get_stimulus_space_positions(stimulus):  # NV: get index of spaces in stimulus

    stimulus_space_positions = []
    for letter_position in range(len(stimulus)):
        if stimulus[letter_position] == " ":
            stimulus_space_positions.append(letter_position)

    return stimulus_space_positions

def get_ngram_edge_position_weight(ngram, ngramLocations, stimulus_space_locations):

    ngramEdgePositionWeight = 0.5  # This is just a default weight; in many cases, it's changed
    # to 1 or 2, as can be seen below.
    max_weight = 2.

    if len(ngram) == 2:
        first = ngramLocations[0]
        second = ngramLocations[1]

        if (first-1) in stimulus_space_locations and (second+1) in stimulus_space_locations:
            ngramEdgePositionWeight = max_weight
        elif (first+1) in stimulus_space_locations and (second-1) in stimulus_space_locations:
            ngramEdgePositionWeight = max_weight
        elif (first-1) in stimulus_space_locations or (second+1) in stimulus_space_locations:
            ngramEdgePositionWeight = 1.
        elif (first+1) in stimulus_space_locations or (second-1) in stimulus_space_locations:
            ngramEdgePositionWeight = 1.
    else:
        letter_location = ngramLocations
        # One letter word
        if letter_location-1 in stimulus_space_locations and letter_location+1 in stimulus_space_locations:
            ngramEdgePositionWeight = max_weight
        # letter at the edge
        elif letter_location-1 in stimulus_space_locations or letter_location+1 in stimulus_space_locations:
            ngramEdgePositionWeight = 1.

    return ngramEdgePositionWeight

def string_to_ngrams_and_locations(stimulus,pm, is_suffix=False):

    stimulus_space_positions = get_stimulus_space_positions(stimulus)
    stimulus = "_" + stimulus + "_"  # GS try to recognize small words better, does not work doing this
    # For the current stimulus, bigrams will be made. Bigrams are only made
    # for letters that are within a range of 4 from each other; (gap=3)

    # Bigrams that contain word boundary letters have more weight.
    # This is done by means of locating spaces in stimulus, and marking
    # letters around space locations (as well as spaces themselves), as
    # indicators of more bigram weight.

    """Returns list with all unique open bigrams that can be made of the stim, and their respective locations 
    (called 'word' for historic reasons), restricted by the maximum gap between two intervening letters."""
    all_bigrams = []
    bigrams_to_locations = {}
    gap = pm.bigram_gap  # None = no limit
    if gap == None:
        for first in range(len(stimulus) - 1):
            if (stimulus[first] == " "):
                continue
            for second in range(first + 1, len(stimulus)):
                if (stimulus[second] == " "):
                    break
                bigram = stimulus[first] + stimulus[second]
                if bigram != '  ':
                    if not bigram in all_bigrams:
                        all_bigrams.append(bigram)
                    bigram_edge_position_weight = get_ngram_edge_position_weight(
                        bigram, (first, second), stimulus_space_positions)
                    if (bigram in bigrams_to_locations.keys()):
                        bigrams_to_locations[bigram].append((first, second, bigram_edge_position_weight))
                    else:
                        bigrams_to_locations[bigram] = [(first, second, bigram_edge_position_weight)]
    else:
        for first in range(len(stimulus) - 1):
            # NV: this code implant is meant to insert special suffix bigrams in bigram list
            # TODO: does not work for prefixes yet
            if (stimulus[first] == " "):  # NV: means that first letter is index 1 or last+1
                if first == 1:  # NV: if it is in the beginning of word
                    if is_suffix:
                        continue  # dont do the special _ at beginning of word if is affix
                    second_alt = 2  # NV: _alt not to interfere with loop variables
                    bigram = '_' + stimulus[second_alt]
                    if not bigram in all_bigrams:
                        all_bigrams.append(bigram)
                    bigram_edge_position_weight = get_ngram_edge_position_weight(
                        bigram, (first, second_alt), stimulus_space_positions)
                    if (bigram in bigrams_to_locations.keys()):
                        bigrams_to_locations[bigram].append((first, second_alt, bigram_edge_position_weight))
                    else:
                        bigrams_to_locations[bigram] = [(first, second_alt, bigram_edge_position_weight)]
                    continue
                elif first == len(stimulus) - 2:  # NV: if first letter is the end space
                    first_alt = -3  # NV: index of last letter
                    # NV: get the actual index (you do +, because first alt is a negative number)
                    first_alt = len(stimulus) + first_alt
                    second_alt = -2  # NV: index of space after last letter
                    second_alt = len(stimulus) + second_alt
                    bigram = stimulus[first_alt] + '_'
                    if not bigram in all_bigrams:
                        all_bigrams.append(bigram)
                    bigram_edge_position_weight = get_ngram_edge_position_weight(
                        bigram, (first_alt, second_alt), stimulus_space_positions)
                    if (bigram in bigrams_to_locations.keys()):
                        bigrams_to_locations[bigram].append((first_alt, second_alt, bigram_edge_position_weight))
                    else:
                        bigrams_to_locations[bigram] = [(first_alt, second_alt, bigram_edge_position_weight)]
                    continue

            # NV:pick letter between first+1 and first+1+gap+1 (end of bigram max length), as long as that is smaller than end of word
            for second in range(first + 1, min(first + 1 + gap + 1, len(stimulus))):
                if (stimulus[
                    second] == " "):  # NV: if that is second lettter, you know you have reached the end of possible bigrams
                    # NV: break out of second loop if second stim is __. This means symbols before word, or when end of word is reached.
                    break
                bigram = stimulus[first] + stimulus[second]
                if bigram != '  ':
                    if not bigram in all_bigrams:
                        all_bigrams.append(bigram)
                    bigram_edge_position_weight = get_ngram_edge_position_weight(
                        bigram, (first, second), stimulus_space_positions)
                    if (bigram in bigrams_to_locations.keys()):
                        bigrams_to_locations[bigram].append((first, second, bigram_edge_position_weight))
                    else:
                        bigrams_to_locations[bigram] = [(first, second, bigram_edge_position_weight)]

    # # GS: test of dit werkt, dan geen monograms, die worden later toch weggefilterd
    #    """Also add monograms"""
    #    for position in range(len(stimulus)):
    #        monogram=stimulus[position]
    #        if(monogram==" "):
    #            continue
    #
    #        if not monogram in allBigrams:
    #            allBigrams_append(monogram)
    #
    #        monogramEdgePositionWeight = get_ngram_edge_position_weight(monogram, position,stimulus_space_positions)
    #        if monogram in bigramsToLocations.keys():
    #            bigramsToLocations[monogram].append((position,monogramEdgePositionWeight))
    #        else:
    #            bigramsToLocations[monogram]=[(position,monogramEdgePositionWeight)]
    # # edge_bigrams = ["_"+stimulus[2], stimulus[-3]+"_"]  # NV: added first and last bigram for affix recognition.

    return all_bigrams, bigrams_to_locations

def normalize_values(p, values, max_value):

    return ((p * max_value) - values) / (p * max_value)

def get_threshold(word, word_freq_dict, max_frequency, freq_p, max_threshold):

    # should always ensure that the maximum possible value of the threshold doesn't exceed the maximum allowable word activity
    # let threshold be fun of word freq. freq_p weighs how strongly freq is (1=max, then thresh. 0 for most freq. word; <1 means less havy weighting)
    # from 0-1, inverse of frequency, scaled to 0(highest freq)-1(lowest freq)
    word_threshold = max_threshold
    try:
        word_frequency = word_freq_dict[word]
        word_threshold = word_threshold * ((max_frequency/freq_p) - word_frequency) / (max_frequency/freq_p)
    except KeyError:
        pass

    return word_threshold

def update_threshold(word_position, word_threshold, max_predictability, pred_p, pred_values):

    word_pred = pred_values[str(word_position)]
    # word_pred = normalize_values(pred_p,float(word_pred),max_predictability)
    word_threshold = word_threshold * ((max_predictability/pred_p) - word_pred) / (max_predictability/pred_p)

    return word_threshold

def is_similar_word_length(len1, len2, len_sim_constant):

    is_similar = False
    # NV: difference of word length  must be within 15% of the length of the longest word
    if abs(len1-len2) < (len_sim_constant * max(len1, len2)):
        is_similar = True

    return is_similar

def build_word_inhibition_matrix(lexicon,lexicon_word_bigrams,pm,tokens_to_lexicon_indices):

    lexicon_size = len(lexicon)
    word_overlap_matrix = np.zeros((lexicon_size, lexicon_size), dtype=int)
    # word_inhibition_matrix = np.empty((lexicon_size, lexicon_size), dtype=bool)

    for word_1_index in range(lexicon_size):
        for word_2_index in range(word_1_index+1,lexicon_size): # AL: make sure word1-word2, but not word2-word1 or word1-word1.
            word1, word2 = lexicon[word_1_index], lexicon[word_2_index]
            if not is_similar_word_length(len(word1), len(word2), pm.word_length_similarity_constant):
                continue
            else:
                bigram_common = list(set(lexicon_word_bigrams[word1][0]).intersection(set(lexicon_word_bigrams[word2][0])))
                n_bigram_overlap = len(bigram_common)
                monograms_common = list(set(word1) & set(word2))
                n_monogram_overlap = len(monograms_common)
                n_total_overlap = n_bigram_overlap + n_monogram_overlap

                if n_total_overlap > pm.min_overlap:
                    word_overlap_matrix[word_1_index, word_2_index] = n_total_overlap - pm.min_overlap
                    word_overlap_matrix[word_2_index, word_1_index] = n_total_overlap - pm.min_overlap
                    # word_inhibition_matrix[word1, word2] = True
                    # word_inhibition_matrix[word2, word1] = True
                else:
                    word_overlap_matrix[word_1_index, word_2_index] = 0
                    word_overlap_matrix[word_2_index, word_1_index] = 0

    output_inhibition_matrix = '../data/Inhibition_matrix_previous.dat'
    with open(output_inhibition_matrix, "wb") as f:
        pickle.dump(np.sum(word_overlap_matrix, axis=0)[tokens_to_lexicon_indices], f)

    size_of_file = os.path.getsize(output_inhibition_matrix)

    with open('../data/Inhib_matrix_params_latest_run.dat', "wb") as f:
        pickle.dump(str(lexicon_word_bigrams) + str(lexicon_size) + str(pm.min_overlap) +
                    # str(complete_selective_word_inhibition) + # str(n_known_words) #str(pm.affix_system) +
                    str(pm.simil_algo) + str(pm.max_edit_dist) + str(pm.short_word_cutoff) + str(size_of_file), f)

    return word_overlap_matrix

def get_blankscreen_stimulus(blankscreen_type):

    if blankscreen_type == 'blank':  # NV decide what type of blank screen to show
        stimulus = ""

    elif blankscreen_type == 'hashgrid':
        stimulus = "#####"  # NV: overwrite stimulus with hash grid

    elif blankscreen_type == 'fixation cross':
        stimulus = "+"

    return stimulus

def get_attention_skewed(attentionWidth, attention_eccentricity, attention_skew):
    # Remember to remove the abs with calc functions
    if attention_eccentricity < 0:
        # Attention left
        attention = 1.0/(attentionWidth)*math.exp(-(pow(abs(attention_eccentricity), 2)) /
                                                  (2*pow(attentionWidth/attention_skew, 2))) + 0.25
    else:
        # Attention right
        attention = 1.0/(attentionWidth)*math.exp(-(pow(abs(attention_eccentricity), 2)) /
                                                  (2*pow(attentionWidth, 2))) + 0.25
    return attention

def calc_acuity(eye_eccentricity, letPerDeg):
    # Parameters from Harvey & Dumoulin (2007); 35.55556 is to make acuity at 0 degs eq. to 1
    return (1/35.555556)/(0.018*(eye_eccentricity*letPerDeg+1/0.64))

def calc_bigram_ext_input(location_info, EyePosition, AttentionPosition, attendWidth, letPerDeg, attention_skew):

    # Here we look up all instances of same bigram. Act of all is summed (this is somewhat of a questionable assumption, perhaps max() would be better
    # todo check if locations weights multiplier is correct fixated words
    bigram_location_weight_multiplier = location_info[2]

    # Bigram activity depends on distance of bigram letters to the centre of attention and fixation and left/right is skewed using negative/positve att_ecc
    attention_eccentricity1 = location_info[0]-AttentionPosition
    attention_eccentricity2 = location_info[1]-AttentionPosition
    eye_eccentricity1 = abs(location_info[0]-EyePosition)
    eye_eccentricity2 = abs(location_info[1]-EyePosition)
    attention1 = get_attention_skewed(attendWidth, attention_eccentricity1, attention_skew)
    attention2 = get_attention_skewed(attendWidth, attention_eccentricity2, attention_skew)

    # Parameters from Harvey & Dumoulin (2007); 35.55556 is to make acuity at 0 degs eq. to 1
    visualAccuity1 = calc_acuity(eye_eccentricity1, letPerDeg)
    visualAccuity2 = calc_acuity(eye_eccentricity2, letPerDeg)

    extInput1 = attention1*visualAccuity1
    extInput2 = attention2*visualAccuity2
    extInput = math.sqrt(extInput1*extInput2)

    sumExtInput = extInput * bigram_location_weight_multiplier

    return sumExtInput

def calc_monogram_ext_input(location_info, EyePosition, AttentionPosition, attendWidth, letPerDeg, attention_skew):

    # Here we look up all instances of same monogram. Act of all is summed
    monogram_locations_weight_multiplier = location_info[1]
    # Monogram activity depends on distance of bigram letters to the centre of attention and fixation

    attention_eccentricity1 = location_info[0]-AttentionPosition
    eye_eccentricity1 = abs(location_info[0]-EyePosition)

    attention1 = get_attention_skewed(attendWidth, attention_eccentricity1, attention_skew)
    visualAccuity1 = calc_acuity(eye_eccentricity1, letPerDeg)

    extInput = attention1*visualAccuity1
    sumExtInput = extInput * monogram_locations_weight_multiplier

    return sumExtInput

def define_slot_matching_order(n_words_in_stim, fixated_position_stimulus):

    # Slot-matching mechanism
    # MM: check len stim, then determine order in which words are matched to slots in stim
    # Words are checked in the order of its attentwght. The closer to the fixation point, the more attention weight.
    # AL: made computation dependent on position of fixated word (so we are not assuming anymore that fixation is always at the center of the stimulus)
    positions = [+1,-1,+2,-2,+3,-3]
    order_match_check = [fixated_position_stimulus]
    for p in positions:
        next_pos = fixated_position_stimulus + p
        if next_pos >= 0 and next_pos < n_words_in_stim:
            order_match_check.append(next_pos)

    return order_match_check

def sample_from_norm_distribution(mu, sigma, distribution_param, recognized):

    if recognized:
        return int(np.round(np.random.normal(mu-distribution_param, sigma, 1)))
    else:
        return int(np.round(np.random.normal(mu, sigma, 1)))

# def find_word_edges(fixation_center,eye_position,stimulus,tokens):
#
#     # contains tuples, tuple[0] is left edge index and tuple[1] is right edge index of words left of fixation + fixated word
#     left_word_edge_letter_indices = []
#     # contains tuples, tuple[0] is left edge index and tuple[1] is right edge index of fixated words + words right of fixation
#     right_word_edge_letter_indices = []
#     # regex used to find indices of word edges
#     p = re.compile(r'\b\w+\b', re.UNICODE)
#
#     # Identify the beginning and end of fixation word by looking at the
#     # first letter following a space, counted to the left of the center,
#     # and the first letter followed by a space, counted to the right from
#     # the center
#     for letter_index in range(int(fixation_center), len(stimulus)):
#         if stimulus[letter_index] == " ":
#             center_word_last_letter_index = letter_index - 1
#             break
#         # in case fixated word is last word in text (no space after last word)
#         elif letter_index == len(stimulus) - 1 and stimulus.split()[-1] == tokens[-1]:
#             center_word_last_letter_index = letter_index
#             break
#
#     for letter_index_reversed in range(int(fixation_center), -1, -1):
#         if stimulus[letter_index_reversed] == " ":
#             center_word_first_letter_index = letter_index_reversed + 1
#             break
#         # in case fixated word is first word in text (no space before first word)
#         elif letter_index_reversed == 0 and stimulus.split()[0] == tokens[0]:
#             center_word_first_letter_index = letter_index_reversed
#             break
#     fixated_word_edge_indices = (center_word_first_letter_index,center_word_last_letter_index)
#
#     fixation_first_position_right_to_middle = eye_position + 1
#     fixation_first_position_left_to_middle = eye_position - 1
#
#     # define stimulus string before and after eye position in fixated word
#     stimulus_before_eyepos, stimulus_after_eyepos = '', ''
#     if fixation_first_position_left_to_middle >= 0:
#         stimulus_before_eyepos = stimulus[0:fixation_first_position_left_to_middle + 1]
#     if fixation_first_position_right_to_middle < len(stimulus):
#         stimulus_after_eyepos = stimulus[fixation_first_position_right_to_middle:-1]
#
#     # Get word edges for all words starting with the word at fixation
#     if stimulus_before_eyepos != '':
#         for m in p.finditer(' ' + stimulus_before_eyepos):
#             left_edge = m.start() - 1
#             right_edge = m.end() - 1
#             if (left_edge, right_edge) != fixated_word_edge_indices: # don't add edges of fixated word
#                 left_word_edge_letter_indices.append((left_edge, right_edge))
#
#     # right_word_edge_letter_indices.append((center_word_first_letter_index, center_word_last_letter_index)) # add edges of fixated word first
#     if stimulus_after_eyepos != '':
#         for m in p.finditer(stimulus_after_eyepos):
#             left_edge = fixation_first_position_right_to_middle + m.start()
#             right_edge = fixation_first_position_right_to_middle + m.end() - 1
#             # for the last letter index of last word in stimulus, HACK to surpass error in regex
#             if right_edge + 2 == len(stimulus):
#                 right_edge = fixation_first_position_right_to_middle + m.end()
#             if (left_edge, right_edge) != fixated_word_edge_indices:  # don't add edges of fixated word
#                 right_word_edge_letter_indices.append((left_edge, right_edge))
#
#     return right_word_edge_letter_indices, left_word_edge_letter_indices, fixation_first_position_right_to_middle, fixation_first_position_left_to_middle, fixated_word_edge_indices

def find_word_edges(stimulus):

    word_edges = dict()

    # AL: regex used to find indices of word edges
    p = re.compile(r'\b\w+\b', re.UNICODE)

    # Get word edges for all words starting with the word at fixation
    for i, m in enumerate(p.finditer(stimulus)):
        word_edges[i] = (m.start(),m.end()-1)

    return word_edges

def get_midword_position_for_surrounding_word(word_position, word_edges, fixated_position_in_stimulus):

    word_center_position = None
    word_position_in_stimulus = fixated_position_in_stimulus + word_position

    # AL: make sure surrounding word is included in stimulus
    if word_position_in_stimulus in word_edges.keys():
        word_slice_length = word_edges[word_position_in_stimulus][1] - word_edges[word_position_in_stimulus][0] + 1
        word_center_position = word_edges[word_position_in_stimulus][0] + round(word_slice_length/2.0) - 1

    return word_center_position

def calc_monogram_attention_sum(position_start, position_end, eye_position, attention_position, attend_width, attention_skew, let_per_deg, foveal_word):

    # this is only used to calculate where to move next when forward saccade
    sum_attention_letters = 0

    for letter_location in range(position_start, position_end+1):
        monogram_locations_weight_multiplier = 0.5
        if foveal_word:
            if letter_location == position_end:
                monogram_locations_weight_multiplier = 2.
        elif letter_location in [position_start, position_end]:
            monogram_locations_weight_multiplier = 2.

        # Monogram activity depends on distance of monogram letters to the centre of attention and fixation
        attention_eccentricity = letter_location - attention_position
        eye_eccentricity = abs(letter_location - eye_position)

        attention = get_attention_skewed(attend_width, attention_eccentricity, attention_skew)
        visual_acuity = calc_acuity(eye_eccentricity, let_per_deg)

        sum_attention_letters += (attention * visual_acuity) * monogram_locations_weight_multiplier

    return sum_attention_letters

def calc_word_attention_right(word_edges, eye_position, attention_position, attend_width, salience_position, attention_skew, let_per_deg, fixated_position_in_stimulus):

    # MM: calculate list of attention wgts for all words in stimulus to right of fix.
    word_attention_right = []
    attention_position += round(salience_position*attend_width)

    for i, edges in word_edges.items():

        # if n or n + x (but not n - x), so only fixated word or words to the right
        if i >= fixated_position_in_stimulus:
            word_start_edge = edges[0]
            word_end_edge = edges[1]

            foveal_word = False
            if i == fixated_position_in_stimulus:
                foveal_word = True

            # if eye position at last letter (right edge) of fixated word
            if foveal_word and eye_position == word_end_edge:
                # set attention wghts for (nonexisting) right part of fixated word to 0
                crt_word_monogram_attention_sum = 0
            else:
                crt_word_monogram_attention_sum = calc_monogram_attention_sum(word_start_edge, word_end_edge, eye_position, attention_position, attend_width, attention_skew, let_per_deg, foveal_word)

            word_attention_right.append(crt_word_monogram_attention_sum)

    return word_attention_right

def calc_saccade_error(saccade_distance, optimal_distance, saccErr_scaler, saccErr_sigma, saccErr_sigma_scaler,use_saccade_error):

    # TODO include fixdur, as in EZ and McConkie (smaller sacc error after longer fixations)
    saccade_error = (optimal_distance - abs(saccade_distance)) * saccErr_scaler
    saccade_error_sigma = saccErr_sigma + (abs(saccade_distance) * saccErr_sigma_scaler)
    saccade_error_norm = np.random.normal(saccade_error, saccade_error_sigma, 1)
    if use_saccade_error:
        return saccade_error_norm
    else:
        return 0.