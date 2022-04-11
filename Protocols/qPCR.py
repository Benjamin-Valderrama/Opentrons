import json
import math

metadata = {
    'protocolName': 'qPCR preparation protocol',
    'author': 'Multiplex <bvalderrama@multiplex.bio>',
    'description': 'Preparation of qPCR after the RT reaction',
    'source': 'Made by multiplex',
    'apiLevel': '2.11'
}


def get_values(*names):
    # Los valores para que las variables custom_* funcione son "yes" o "no"

    # Máximo valor de RT_sample_number es 86 -> columnas 1 a 10: completas; columna 11: 2 muestras + 6 controles y columna 12: bloqueda
    _all_values = json.loads("""{"RT_sample_number":28,

    "custom_tiprack":"no", "custom_rt_plate":"no", "replicates":2}""")
    return [_all_values[n] for n in names]


def run(protocol):
    [RT_sample_number,
     custom_tiprack, custom_rt_plate,
     replicates] = get_values(
        "RT_sample_number",
        "custom_tiprack", "custom_rt_plate",
        "replicates"
    )

    # TIPS
    slots = ['5', '8', '11']
    special_slots = ['10']

    tipracks = [protocol.load_labware('opentrons_96_tiprack_20ul', slot, 'tiprack') for slot in slots]
    special_tiprack = [protocol.load_labware('opentrons_96_tiprack_20ul', slot, 'special tiprack') for slot in
                       special_slots]  # Tiprack for pipetting with less than 8 channels

    # INSTRUMENTS
    m20 = protocol.load_instrument('p20_multi_gen2', 'right', tip_racks=tipracks)
    s20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=tipracks)

    # LABWARE:

    # Master Mix (Eppendorf tubes rack)
    eppendorf_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 2, 'eppendorf rack')

    mastermix = eppendorf_rack.wells()[0]  # A1
    eppendorf_con_control_positivo = eppendorf_rack.wells()[-1]  # D6
    eppendorf_con_control_negativo = eppendorf_rack.wells()[-2]  # C6

    # RT related labware:

    # Loading plates with the RT samples
    if custom_rt_plate == 'yes':
        rt_plate = protocol.load_labware('nest_96_wellplate_300ul_skirtless', 1, 'RT sample plate')

    else:
        rt_plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 1, 'RT sample plate')

    # q-PCR related labware:

    # Calculating how many wells (samples + controls) we gonna use for RT:
    number_of_wells_for_pcr = (RT_sample_number + 2) * replicates
    needed_pcr_plates = math.ceil(
        number_of_wells_for_pcr / 84)  # 84 is the max number of samples we can deal with in one plate

    # Loading the required plates for the rt-PCR ractions (rx)
    pcr_slots = ['4', '7'][:needed_pcr_plates]
    pcr_plates = [protocol.load_labware('biorad_96_wellplate_200ul_pcr', slot, 'q-PCR output plate') for slot in
                  pcr_slots]  # It need to be biorad plates as output PCR plate

    # print("\npcr_plates : ", pcr_plates)
    print("RT_sample_number : ", RT_sample_number)

    # Custom function: Take a list of plates (or just one plate) and define which are columns are completed and which ones are incompleted
    def column_classifier(list_of_plates):

        col_number = math.ceil(RT_sample_number / 8)
        num_of_complete_cols_plate = divmod(RT_sample_number, 8)[0]

        if RT_sample_number % 8 == 0:  # If all columns are full of samples
            # Check whether the input of the function was a list of plates ...
            if type(list_of_plates) == list:
                plate_complete_cols = [col for plate in list_of_plates for col in
                                       plate.rows()[0][:num_of_complete_cols_plate]]
                plate_incomplete_cols = [col for plate in list_of_plates for col in
                                         plate.rows()[0][num_of_complete_cols_plate:num_of_complete_cols_plate]]

            else:  # or not (input was just one plate)
                plate_complete_cols = [col for col in list_of_plates.rows()[0][:num_of_complete_cols_plate]]
                plate_incomplete_cols = [col for col in list_of_plates.rows()[0][
                                                        num_of_complete_cols_plate:num_of_complete_cols_plate]]  # Empty list

        else:  # There are no incomplete cols
            # Check whether the input of the function was a list of plates ...
            if type(list_of_plates) == list:
                plate_complete_cols = [col for plate in list_of_plates for col in
                                       plate.rows()[0][:num_of_complete_cols_plate]]
                plate_incomplete_cols = [col for plate in list_of_plates for col in
                                         plate.rows()[0][num_of_complete_cols_plate:col_number]]

            else:  # or not (input was just one plate)
                plate_complete_cols = [col for col in list_of_plates.rows()[0][:num_of_complete_cols_plate]]
                plate_incomplete_cols = [col for col in
                                         list_of_plates.rows()[0][num_of_complete_cols_plate:col_number]]  # Empty list

        return [plate_complete_cols,
                plate_incomplete_cols]  # Subset the function's output with 0 for complete columns and 1 for incomplete columns.

    # Custom function: It makes a flat list out of a nested list
    def list_flattener(list):
        return [item for sublist in list for item in sublist]

    # Custom function : Takes a list of plates (or just one plate), slice each of them on the half and gives just *one flat* list for each side of all plates on the list
    def slice_list_of_plates(list_of_plates, plate_type):  # plate_type puede ser rt o qpcr

        # Check whether list of plates was indeed a list of paltes
        if plate_type == "qpcr":
            nested_plates = [plate.rows()[0] for plate in list_of_plates]

            nested_plates_left = [plate[:len(plate) // 2] for plate in nested_plates]
            nested_plates_right = [plate[len(plate) // 2:] for plate in nested_plates]

            if len(pcr_slots) > 1:
                first_replicate_plate = [nested_plates_left[0], nested_plates_right[0]]
                second_replicate_plate = [nested_plates_left[1], nested_plates_right[1]]
                plates_with_replicates = [first_replicate_plate, second_replicate_plate]

            else:
                plates_with_replicates = [nested_plates_left[0], nested_plates_right[0]]

            return plates_with_replicates


        elif plate_type == "rt":  # Or, on the other hand, if it was just one plate
            plate_left = list_of_plates.rows()[0][:len(list_of_plates.columns()) // replicates]
            plate_right = list_of_plates.rows()[0][len(list_of_plates.columns()) // replicates:]

            return [plate_left, plate_right]  # Subset the function's output with 0 for left and 1 for right side.

    # PLATES SLICED:
    rt_plate_left = slice_list_of_plates(rt_plate, "rt")[0]
    rt_plate_right = slice_list_of_plates(rt_plate, "rt")[1]
    # print("\nRT_sample_number : ", RT_sample_number)

    nested_list_of_sliced_qpcr_plates = slice_list_of_plates(pcr_plates, "qpcr")
    # print("\nnested_list_of_sliced_qpcr_plates : ", nested_list_of_sliced_qpcr_plates)

    first_qpcr_replicate = nested_list_of_sliced_qpcr_plates[0]
    # print("\nfirst_pcrplate_by_halves : ", first_qpcr_replicate)

    second_qpcr_replicate = nested_list_of_sliced_qpcr_plates[1]
    # print("\nsecond_pcrplate_by_halves : ", second_qpcr_replicate)

    # THE INTENTION OF THIS CHUNK OF CODE IS TO HAVE THE SAME NAMES FOR THE VARIABLES REGARDLESS OF THE NUMBER OF PCR PLATES USED
    if len(pcr_slots) < 2:  # If we need to use just one pcr plate
        first_half_of_RT_samples = first_qpcr_replicate
        # print("\nfirst_half_of_RT_samples : ", first_half_of_RT_samples)
        second_half_of_RT_samples = second_qpcr_replicate
        # print("\nsecond_half_of_RT_samples : ", second_half_of_RT_samples)

        wells_for_reaction_2x_preparation = first_half_of_RT_samples
        # print("\nwells_for_reaction_2x_preparation : ", wells_for_reaction_2x_preparation)
        wells_for_reaction_2x_replicate = second_half_of_RT_samples
        # print("\nwells_for_reaction_2x_replicate : ", wells_for_reaction_2x_replicate)

    else:  # If we need to use 2 pcr plates
        first_half_of_RT_samples = first_qpcr_replicate
        # print("\nfirst_half_of_RT_samples : ", first_half_of_RT_samples)
        second_half_of_RT_samples = second_qpcr_replicate
        # print("\nsecond_half_of_RT_samples : ", second_half_of_RT_samples)

        wells_for_reaction_2x_preparation = list_flattener([first_half_of_RT_samples[0], second_half_of_RT_samples[0]])
        # print("\nwells_for_reaction_2x_preparation : ", wells_for_reaction_2x_preparation)
        wells_for_reaction_2x_replicate = list_flattener([first_half_of_RT_samples[1], second_half_of_RT_samples[1]])
        # print("\nwells_for_reaction_2x_replicate : ", wells_for_reaction_2x_replicate)

    rt_plate_complete_cols = column_classifier(rt_plate)[0]
    # print("\nrt_plate_complete_cols : ", rt_plate_complete_cols)
    rt_plate_incomplete_cols = column_classifier(rt_plate)[1]
    # print("\nrt_plate_incomplete_cols : ", rt_plate_incomplete_cols)

    pcr_plates_complete_cols = column_classifier(pcr_plates)[0]
    # print("\npcr_plates_complete_cols : ", pcr_plates_complete_cols)
    pcr_plates_incomplete_cols = column_classifier(pcr_plates)[1]
    # print("\npcr_plates_incomplete_cols : ", pcr_plates_incomplete_cols)

    # COMMANDS

    # qPCR - PASO 1: 14.25 uL de Master Mix desde el eppendorf tube rack hacia en cada pocillo del PCR plate
    protocol.comment("\nMaster Mix")
    mastermix_volume = 14.25
    output_wells = [well for plate in pcr_plates for well in
                    plate.wells()[:(RT_sample_number + 2)]]  # +2 due to the two new controls

    nested_plates = [plate.wells() for plate in pcr_plates]
    list_of_wells_for_reaction_2x_preparation = list_flattener([plate[:len(plate) // 2] for plate in nested_plates])[
                                                :RT_sample_number + 2]
    # print("\nlist_of_wells_for_reaction_2x_preparation : ", list_of_wells_for_reaction_2x_preparation)
    list_of_wells_for_reaction_2x_replicate = list_flattener([plate[len(plate) // 2:] for plate in nested_plates])[
                                              :RT_sample_number + 2]
    # print("\nlist_of_wells_for_reaction_2x_replicate : ", list_of_wells_for_reaction_2x_replicate)

    s20.flow_rate.aspirate = 2
    s20.flow_rate.dispense = 2
    s20.flow_rate.blow_out = 2

    s20.pick_up_tip()
    for i in range(2):  # In range 2 porque estamos haciendo duplicados
        for preparation_well in list_of_wells_for_reaction_2x_preparation:
            s20.aspirate(mastermix_volume, mastermix)
            s20.move_to(mastermix.top(), speed=3)
            s20.dispense(s20.current_volume, preparation_well)
    s20.drop_tip()

    # qPCR - PASO 2: 0.75 uL de Templado desde el RT plate hacia el PCR plate
    template_volume_in_2x_reaction = 2  # uL

    # TRANSFER TO COMPLETE COLUMNS
    protocol.comment("\nComplete Columns")

    m20.flow_rate.aspirate = 5
    m20.flow_rate.dispense = 5
    m20.flow_rate.blow_out = 2

    num_complete_cols = len(rt_plate_complete_cols)
    complete_cols_for_2x_reaction_preparation = [col for col in wells_for_reaction_2x_preparation if
                                                 col in pcr_plates_complete_cols][:num_complete_cols]
    # print("\ncomplete_cols_for_2x_reaction_preparation : ", complete_cols_for_2x_reaction_preparation)

    complete_cols_for_2x_reaction_replicates = [col for col in wells_for_reaction_2x_replicate[
                                                               :len(complete_cols_for_2x_reaction_preparation)]]
    # print("\ncomplete_cols_for_2x_reaction_replicates : ", complete_cols_for_2x_reaction_replicates)

    for rt_sample_col, qpcr_comp_col in zip(rt_plate_complete_cols, complete_cols_for_2x_reaction_preparation):
        m20.pick_up_tip()
        m20.aspirate(template_volume_in_2x_reaction, rt_sample_col)
        m20.touch_tip(v_offset=-0.5, speed=50)
        m20.dispense(m20.current_volume, qpcr_comp_col)
        m20.blow_out(qpcr_comp_col.top(z=-2))
        m20.touch_tip(qpcr_comp_col, v_offset=-0.5, speed=50)
        m20.drop_tip()

    # TRANSFER TO INCOMPLETE COLUMNS
    protocol.comment("\nIncomplete Columns")

    m20 = protocol.load_instrument('p20_multi_gen2', 'right', replace=True)

    m20.flow_rate.aspirate = 5
    m20.flow_rate.dispense = 5
    m20.flow_rate.blow_out = 2

    if RT_sample_number % 8 == 0:
        # If the colum will be filled when we add the controls, then we have 6 samples in the incomplete colum
        num_wells_on_incomplete_cols = 6

    else:
        num_wells_on_incomplete_cols = divmod(RT_sample_number, 8)[1]

    num_channels_per_pickup = num_wells_on_incomplete_cols

    per_tip_pickup_current = 0.075
    # (current required for picking up one tip, do not modify unless
    # you are using a GEN2 P300 8-Channel in which case change it to
    # 0.1)
    # (for GEN2 P20 8-Channel, current must be 0.075)

    pick_up_current = num_channels_per_pickup * per_tip_pickup_current

    protocol._implementation._hw_manager.hardware._attached_instruments[
        m20._implementation.get_mount()
    ].update_config_item('pick_up_current', pick_up_current)

    # List of tips. Ordered based on the num_channels_per_pickup selected before.
    tips_ordered = [
        tip for rack in special_tiprack
        for row in rack.rows()[
                   len(rack.rows())
                   - num_channels_per_pickup::-1 * num_channels_per_pickup]
        for tip in row]

    tip_count = 0

    def special_pick_up(pip):
        nonlocal tip_count
        pip.pick_up_tip(tips_ordered[tip_count])
        tip_count += 1

    incomplete_cols_for_2x_reaction_preparation = [col for col in wells_for_reaction_2x_preparation if
                                                   col in pcr_plates_incomplete_cols]
    # print("\nincomplete_cols_for_2x_reaction_preparation : ", incomplete_cols_for_2x_reaction_preparation)

    incomplete_cols_for_2x_reaction_replicates = [col for col in wells_for_reaction_2x_replicate[
                                                                 len(complete_cols_for_2x_reaction_preparation):len(
                                                                     complete_cols_for_2x_reaction_preparation) + 1]]
    # print("\nincomplete_cols_for_2x_reaction_replicates : ", incomplete_cols_for_2x_reaction_replicates)

    for rt_sample_col, qpcr_incomp_col in zip(rt_plate_incomplete_cols, incomplete_cols_for_2x_reaction_preparation):
        special_pick_up(m20)
        m20.aspirate(template_volume_in_2x_reaction, rt_sample_col)
        m20.touch_tip(v_offset=-0.5, speed=50)
        m20.dispense(m20.current_volume, qpcr_incomp_col)
        m20.blow_out(qpcr_incomp_col.top(z=-2))
        m20.touch_tip(qpcr_incomp_col, v_offset=-0.5, speed=50)
        m20.drop_tip()

    # qPCR - PASO 3: 0.75 uL de Control +/- desde el eppendorf tuberack hacia el PCR plate
    control_positivo_preparation_well = list_of_wells_for_reaction_2x_preparation[-2]
    # print("\ncontrol_positivo_preparation_well : ", control_positivo_preparation_well)
    control_negativo_preparation_well = list_of_wells_for_reaction_2x_preparation[-1]
    # print("\ncontrol_negativo_preparation_well : ", control_negativo_preparation_well)

    control_positivo_replicate_well = list_of_wells_for_reaction_2x_replicate[-2]
    # print("\ncontrol_positivo_replicate_well : ", control_positivo_replicate_well)
    control_negativo_replicate_well = list_of_wells_for_reaction_2x_replicate[-1]
    # print("\ncontrol_negativo_replicate_well : ", control_negativo_replicate_well)

    # Control +
    protocol.comment("\nControl +")

    s20.flow_rate.aspirate = 5
    s20.flow_rate.dispense = 5
    s20.flow_rate.blow_out = 2

    control_volume_in_2x_reaction = 2  # uL

    s20.pick_up_tip()
    s20.aspirate(control_volume_in_2x_reaction, eppendorf_con_control_positivo)
    s20.touch_tip(v_offset=-0.5, speed=50)
    s20.dispense(s20.current_volume, control_positivo_preparation_well)
    s20.blow_out(control_positivo_preparation_well.top(z=-0.5))
    s20.touch_tip(v_offset=-0.5, speed=50)
    s20.drop_tip()

    # Control -
    protocol.comment("\nControl -")

    s20.pick_up_tip()
    s20.aspirate(template_volume_in_2x_reaction, eppendorf_con_control_negativo)
    s20.touch_tip(v_offset=-0.5, speed=50)
    s20.dispense(s20.current_volume, control_negativo_preparation_well)
    s20.blow_out(control_negativo_preparation_well.top(z=-0.5))
    s20.touch_tip(v_offset=-0.5, speed=50)
    s20.drop_tip()

    # qPCR - PASO 4: Hacer que la reacción 2x sea dividida en dos pocillos, c/u con reacción 1x

    # SPLITING 2X REACTION FROM INCOMPLETE COLUMNS IN 2 1X REACTIONS
    protocol.comment("\nSplitting Incomplete Columns")

    for well_preparation, well_replicate in zip(incomplete_cols_for_2x_reaction_preparation,
                                                incomplete_cols_for_2x_reaction_replicates):
        special_pick_up(m20)
        m20.mix(5, 20, well_preparation)
        m20.aspirate(15, well_preparation)
        m20.touch_tip(well_preparation, v_offset=-0.5, speed=50)
        m20.dispense(m20.current_volume, well_replicate)
        m20.blow_out(well_replicate.top(z=-0.5))
        m20.touch_tip(well_replicate, v_offset=-0.5, speed=50)
        m20.drop_tip()

    # SPLITING 2X REACTION FROM COMPLETE COLUMNS IN 2 1X REACTIONs
    protocol.comment("\nSplitting Complete Columns")

    tipracks = [protocol.load_labware('opentrons_96_tiprack_20ul', '3', 'tiprack')]
    m20 = protocol.load_instrument('p20_multi_gen2', 'right', tip_racks=tipracks, replace=True)

    m20.flow_rate.aspirate = 5
    m20.flow_rate.dispense = 5
    m20.flow_rate.blow_out = 2

    for well_preparation, well_replicate in zip(complete_cols_for_2x_reaction_preparation,
                                                complete_cols_for_2x_reaction_replicates):
        m20.pick_up_tip()
        m20.mix(5, 20, well_preparation)
        m20.aspirate(15, well_preparation)
        m20.touch_tip(well_preparation, v_offset=-0.5, speed=50)
        m20.dispense(m20.current_volume, well_replicate)
        m20.blow_out(well_replicate.top(z=-0.5))
        m20.touch_tip(well_replicate, v_offset=-0.5, speed=50)
        m20.drop_tip()

    # SPLITTING 2X REACTION FROM + CONTROL IN 2 1X REACTIONS
    protocol.comment("\nSplitting Positive Control")
    s20.pick_up_tip()
    s20.mix(5, 20, control_positivo_preparation_well)
    s20.aspirate(15, control_positivo_preparation_well)
    s20.touch_tip(control_positivo_preparation_well, v_offset=-0.5, speed=50)
    s20.dispense(s20.current_volume, control_positivo_replicate_well)
    s20.blow_out(control_positivo_replicate_well.top(z=-0.5))
    s20.touch_tip(control_positivo_replicate_well, v_offset=-0.5, speed=50)
    s20.drop_tip()

    # SPLITTING 2X REACTION FROM - CONTROL IN 2 1X REACTIONS
    protocol.comment("\nSplitting Negative Control")
    s20.pick_up_tip()
    s20.mix(5, 20, control_negativo_preparation_well)
    s20.aspirate(15, control_negativo_preparation_well)
    s20.touch_tip(control_negativo_preparation_well, v_offset=-0.5, speed=50)
    s20.dispense(s20.current_volume, control_negativo_replicate_well)
    s20.blow_out(control_negativo_replicate_well.top(z=-0.5))
    s20.touch_tip(control_negativo_replicate_well, v_offset=-0.5, speed=50)
    s20.drop_tip()

    # qPCR - PASO 5: Realizar el qPCR
    if len(pcr_slots) <= 1:
        protocol.comment("\nRetirar las output plates (slot '4') y realizar el programa de qPCR en el termociclador")
    else:
        protocol.comment(
            "\nRetirar las output plates (slots '4' y '7') y realizar el programa de qPCR en el termociclador")