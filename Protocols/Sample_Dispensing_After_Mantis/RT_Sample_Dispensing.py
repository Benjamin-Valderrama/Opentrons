import json

metadata = {
    'protocolName': 'RT sample distribution',
    'author': 'Multiplex <bvalderrama@multiplex.bio>',
    'description': 'RTs samples distribution. This script can handle up to 3 extraction plates and has to be used after dispensing the mastermix with Mantis',
    'source': 'Made by multiplex',
    'apiLevel': '2.11'
}


def get_values(*names):
    # Sample number = cantidad de muestras incluidos los controles positivo y negativo de la extracción

    # los valores para que las variables custom_* funcione son "yes" o "no"

    # La variable 'sample_number' puede tomar hasta 3 valores.

    # Ejemplo 1: [19, 53, 40]. Esto quiere decir que el primer plate tiene 19 muestras, el segundo 53, y el tercero 40
    # Ejemplo 2: [50]. Esto quiere decir que se va a procesar sólo una placa y que esta tiene 50 muestras
    # Ejemplo 3: [8, 43]. Esto quiere decir que se van a procesar 2 placas. Una de 8 muestras y la otra de 43 muestras.
    _all_values = json.loads("""{"sample_number":[1, 3, 2],

    "custom_tipracks":"no" , "custom_sample_plate":"yes", "custom_output_plate":"no"}""")
    return [_all_values[n] for n in names]


def run(protocol):
    [sample_number,
     custom_tipracks, custom_sample_plate, custom_output_plate] = get_values(
        "sample_number",
        "custom_tipracks", "custom_sample_plate", "custom_output_plate"
    )

    # LABWARE DEFINITIONS:

    # Import RNA plates (96 well plates)
    samples_slots = ['4', '5', '6'][:len(sample_number)]

    if custom_sample_plate == 'yes':
        sample_plates = [protocol.load_labware('nest_96_wellplate_200ul_cap', slot, 'plate with RNA samples') for slot
                         in samples_slots]
    else:
        sample_plates = [protocol.load_labware('biorad_96_wellplate_200ul_pcr', slot, 'plate with RNA samples') for slot
                         in samples_slots]

    # Import Output plates
    output_slots = ['1', '2', '3'][:len(sample_number)]

    if custom_output_plate == 'yes':
        output_plates = [protocol.load_labware('chancho_96wells_300ul_semiskirt', slot, 'output plate') for slot in
                         output_slots]
    else:
        output_plates = [protocol.load_labware('biorad_96_wellplate_200ul_pcr', slot, 'output plate') for slot in
                         output_slots]

    # Import Tips
    tip_slots = ['7', '8', '9'][:len(sample_number)]

    if custom_tipracks == 'yes':
        # OJO: Las custom tipracks para p20 no están implementadas aún. Es probable que no sea necesario crear el labware_definition hasta en un buen tiempo.
        tipracks = [protocol.load_labware('vertex_96_tiprack_20ul', slot, 'tiprack') for slot in tip_slots]
    else:
        tipracks = [protocol.load_labware('opentrons_96_tiprack_20ul', slot, 'tiprack') for slot in tip_slots]

    # Import Eppendorf tube rack
    eppendorf_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 11, 'eppendorf rack')

    # Defining specific wells within the Eppendorf tube rack
    eppendorf_control_positivo = eppendorf_rack.wells()[0]  # A1
    eppendorf_control_negativo = eppendorf_rack.wells()[-1]  # D6

    # Loading INSTRUMENTS:
    m20 = protocol.load_instrument('p20_multi_gen2', 'right', tip_racks=tipracks)
    s20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=tipracks)

    # DEFINIMOS EL NUMERO DE COLUMNAS COMPLETAS Y, DENTRO DE LA COLUMNA QUE QUEDA INCOMPLETA, CALCULAMOS LA CANTIDAD DE POCILLOS CON MUESTRAS

    # Por 'num_cols_completas' sabemos el número de columnas completas que hay en cada placa.
    num_cols_completas = [divmod(number, 8)[0] for number in sample_number]

    # Por 'num_pocillos_col_incompleta' sabemos cuantos pocillos de la columna incompleta tienen muestras, lo que nos permite tomar el número exacto de puntas necesarias.
    num_pocillos_col_incompleta = [divmod(number, 8)[1] for number in sample_number]

    # LISTA CON LAS COLUMNAS COMPLETAS EN CADA RACK
    protocol.comment("\nCOMPLETE COLUMNS :")

    # PREPARACIÓN DE LISTAS:

    # LISTA1: La 'list_of_complete_columns_through_sample_plates' es una lista. Cada elemento es, a su vez, una lista con todas las columnas que están completas de muestras en cada una de las plates que tienen samples
    list_of_complete_columns_through_sample_plates = []

    for num, plate in zip(num_cols_completas, sample_plates):
        for col in plate.rows()[0][:num]:
            list_of_complete_columns_through_sample_plates.append(col)

    # LISTA2: La 'list_of_complete_columns_through_output_plates' es una lista. Cada elemento es, a su vez, una lista con todas las columnas que están completas de muestras en cada una de las plates que tendrán el output
    list_of_complete_columns_through_output_plates = []

    for num, plate in zip(num_cols_completas, output_plates):
        for col in plate.rows()[0][:num]:
            list_of_complete_columns_through_output_plates.append(col)

    # LISTA3: La 'lista_de_tips' es una lista de listas. Cada elemento es, a su vez, una lista con todas las columnas con puntas de cada rack
    lista_de_tips = []
    for rack, numero in zip(tipracks, num_cols_completas):
        lista_de_tips.append(rack.rows()[0][:numero])

    lista_de_tips = [subelement for element in lista_de_tips for subelement in
                     element]  # Make the previous list 'lista_de_puntas' a flat list

    # Transfering the RNA from sample_plates to output_plates (Complete columns only)
    m20.well_bottom_clearance.aspirate = 0.6
    m20.well_bottom_clearance.dispense = 0.6

    for sample_col, output_col, tip_col in zip(list_of_complete_columns_through_sample_plates,
                                               list_of_complete_columns_through_output_plates, lista_de_tips):
        m20.pick_up_tip(tip_col)
        m20.mix(10, 5, sample_col)
        m20.aspirate(2, sample_col)
        m20.dispense(m20.current_volume, output_col)
        m20.blow_out(output_col.top(z=-1))
        m20.touch_tip(v_offset=-0.5, speed=50)
        m20.drop_tip()

    # Transfering the RNA from sample_plates to output_plates (Incomplete columns only)
    protocol.comment("\nINCOMPLETE COLUMNS :")

    # LISTA CON LAS COLUMNAS INCOMPLETAS EN CADA RACK

    # La 'list_of_incomplete_columns_through_racks' es una lista. Cada elemento es, a su vez, una lista con todas las columnas que no están completas
    list_of_incomplete_columns_through_sample_plates = []

    for num_complete, num_incomplete, plate in zip(num_cols_completas, num_pocillos_col_incompleta, sample_plates):
        if num_incomplete == 0:  # Si el número de pocillos en la columna incompleta es == 0 (es deci, esa plate no tiene columnas incompletas), se pasa al siguiente plate
            list_of_incomplete_columns_through_sample_plates.append(None)
        else:
            # En caso de que el plate tenga una columna incompleta, se guarda cuantos pocillos tienen esa columna incompleta para que la pipeta tome el número exacto de tips necesarios
            for col in plate.rows()[0][num_complete:num_complete + 1]:
                list_of_incomplete_columns_through_sample_plates.append(col)

    list_of_incomplete_columns_through_output_plates = []

    for num_complete, num_incomplete, plate in zip(num_cols_completas, num_pocillos_col_incompleta, output_plates):
        if num_incomplete == 0:  # Si el número de pocillos en la columna incompleta es == 0 (es deci, esa plate no tiene columnas incompletas), se pasa al siguiente plate
            list_of_incomplete_columns_through_output_plates.append(None)
        else:
            # En caso de que el plate tenga una columna incompleta, se guarda cuantos pocillos tienen esa columna incompleta para que la pipeta tome el número exacto de tips necesarios
            for col in plate.rows()[0][num_complete:num_complete + 1]:
                list_of_incomplete_columns_through_output_plates.append(col)

    special_pick_up_tip_list = []

    for rack, num_complete_cols, num_wells_incomp_col in zip(tipracks, num_cols_completas, num_pocillos_col_incompleta):
        if num_wells_incomp_col != 0:  # There is an incomplete column in that rack
            special_pick_up_tip_list.append(
                [subelement for element in rack.columns()[num_complete_cols:num_complete_cols + 1] for subelement in
                 element][8 - num_wells_incomp_col])

        else:  # All columns in that rack are complete columns
            special_pick_up_tip_list.append(None)

    m20.well_bottom_clearance.aspirate = 0.6
    m20.well_bottom_clearance.dispense = 0.6

    # Definimos la cantiad de corriente (y potencia mecánica) que usará el robot para tomar las puntas necesarias. La cantidad de fuerza es proporcional a la cantidad de tips que se van a tomar, por lo que este es un paso crítico.
    per_tip_pickup_current = .075  # 0.075 para p20 y 0.1 para p300

    for sample_col, output_col, num_incomplete_wells, tips in zip(list_of_incomplete_columns_through_sample_plates,
                                                                  list_of_incomplete_columns_through_output_plates,
                                                                  num_pocillos_col_incompleta,
                                                                  special_pick_up_tip_list):

        if num_incomplete_wells != 0 and tips != None:  # Si la columna está incompleta, entonces:
            # Definimos la cantidad de corriente que se va a usar para el pick up (dependiendo de la cantidad de tips que se necesitan tomar)
            pick_up_current = num_incomplete_wells * per_tip_pickup_current

            protocol._implementation._hw_manager.hardware._attached_instruments[
                m20._implementation.get_mount()
            ].update_config_item('pick_up_current', pick_up_current)

            m20.pick_up_tip(tips)
            m20.mix(10, 5, sample_col)
            m20.aspirate(2, sample_col)
            m20.dispense(m20.current_volume, output_col)
            m20.blow_out(output_col.top(z=-1))
            m20.touch_tip(v_offset=-0.5, speed=50)
            m20.drop_tip()

    protocol.comment("\nPOSITIVE CONTROLS : ")
    # Transfering the Positive Controls from TubeRack to output_plates
    for total_number_of_samples, plate in zip(sample_number, output_plates):
        s20.pick_up_tip()
        s20.mix(10, 5, eppendorf_control_positivo)
        s20.aspirate(2, eppendorf_control_positivo)
        s20.touch_tip(v_offset=-0.5, speed=50)
        s20.dispense(s20.current_volume, plate.wells()[total_number_of_samples])
        s20.blow_out(plate.wells()[total_number_of_samples].top(z=-1))
        s20.touch_tip(v_offset=-0.5, speed=50)
        s20.drop_tip()

    protocol.comment("\nNEGATIVE CONTROLS : ")
    # Transfering the Negative Controls from TubeRack to output_plates
    for total_number_of_samples, plate in zip(sample_number, output_plates):
        s20.pick_up_tip()
        s20.mix(10, 5, eppendorf_control_negativo)
        s20.aspirate(2, eppendorf_control_negativo)
        s20.touch_tip(v_offset=-0.5, speed=50)
        s20.dispense(s20.current_volume, plate.wells()[total_number_of_samples + 1])
        s20.blow_out(plate.wells()[total_number_of_samples + 1].top(z=-1))
        s20.touch_tip(v_offset=-0.5, speed=50)
        s20.drop_tip()