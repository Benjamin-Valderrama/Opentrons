import json

metadata = {
    'protocolName': 'qPCR sample distribution',
    'author': 'Multiplex <bvalderrama@multiplex.bio>',
    'description': 'qPCRs samples distribution. This script can handle up to 2 plates with RT samples and has to be used after dispensing the mastermix with Mantis',
    'source': 'Made by multiplex',
    'apiLevel': '2.11'
}


def get_values(*names):
    # Sample number = cantidad de muestras incluidos los controles positivo y negativo de la extracción

    # los valores para que las variables custom_* funcione son "yes" o "no"

    # La variable 'sample_number' puede tomar hasta 3 valores.

    # Ejemplo 1: [50]. Esto quiere decir que se va a procesar sólo una placa y que esta tiene 50 muestras
    # Ejemplo 2: [8, 43]. Esto quiere decir que se van a procesar 2 placas. Una de 8 muestras y la otra de 43 muestras.
    _all_values = json.loads("""{"sample_number":[10],

    "custom_tipracks":"no" , "custom_sample_plate":"no", "custom_output_plate":"no"}""")
    return [_all_values[n] for n in names]


def run(protocol):
    [sample_number,
     custom_tipracks, custom_sample_plate, custom_output_plate] = get_values(
        "sample_number",
        "custom_tipracks", "custom_sample_plate", "custom_output_plate"
    )

    # Import Tips
    tip_slots = ['10', '11'][:len(sample_number)]

    if custom_tipracks == 'yes':
        # Las custom tipracks para p20 no están implementadas aún.
        tipracks = [protocol.load_labware('vertex_96_tiprack_20ul', slot, 'tiprack') for slot in tip_slots]
    else:
        tipracks = [protocol.load_labware('opentrons_96_tiprack_20ul', slot, 'tiprack') for slot in tip_slots]

    # Import cDNA plates (96 well plates)
    samples_slots = ['7', '8'][:len(sample_number)]
    if custom_sample_plate == 'yes':
        sample_plates = [protocol.load_labware('chancho_96wells_300ul_semiskirt', slot, 'plate with RNA samples') for
                         slot in samples_slots]
    else:
        sample_plates = [protocol.load_labware('biorad_96_wellplate_200ul_pcr', slot, 'plate with RNA samples') for slot
                         in samples_slots]

    # Plates with mastermix that are waiting for template (96 well plates)
    output_slots_set1 = ['4', '5'][:len(sample_number)]
    available_slots_set2 = ['1', '2'][:len(
        sample_number)]  # Esta lista contiene posiciones que están disponibles, pero aún no se sabe si van a ser usadas o no.

    # Definimos la cantidad de placas que van a ser usadas en función de la cantidad de muestras en cada placa de las sample_plates:
    # Si algún 'sample_number' es mayor a 46, entonces tendremos que usar 2 output_plates. Esta condicion es checkeada en el siguiente statement
    output_slots_set2 = []
    for sampleNumber, slot_set2 in zip(sample_number, available_slots_set2):
        if sampleNumber <= 46:  # Si son 46 muestras o menos en el sample_plate, entonces no se va a usar el 2do plate
            output_slots_set2.append(None)
        else:  # Si el sample_plate tiene más de 46 muestras, entonces se va a usar un segundo plate
            output_slots_set2.append(slot_set2)
            # print("output_slots_set2 : ", output_slots_set2)

    # Podemos elegir placas customizadas
    if custom_output_plate == 'yes':
        output_plates1 = [protocol.load_labware('chancho_96wells_300ul_semiskirt', slot, 'output plate') for slot in
                          output_slots_set1]
        # En caso de que se tengan que usar 2 output_plates para una misma sample_plate (porque tiene más de 46 muestras), indicamos en qué parte del deck se encontraran esas 2 plates
        output_plates2 = []
        for slot in output_slots_set2:
            if slot is not None:
                output_plates2.append(protocol.load_labware('chancho_96wells_300ul_semiskirt', slot, 'output plate'))
            else:  # Si no se usan 2 output_plates, se explicita eso con un None
                output_plates2.append(None)

    else:  # No queremos usar placas customizadas
        output_plates1 = [protocol.load_labware('biorad_96_wellplate_200ul_pcr', slot, 'output plate') for slot in
                          output_slots_set1]
        # En caso de que se tengan que usar 2 output_plates para una misma sample_plate (porque tiene más de 46 muestras), indicamos en qué parte del deck se encontraran esas 2 plates
        output_plates2 = []
        for slot in output_slots_set2:
            if slot is not None:
                output_plates2.append(protocol.load_labware('biorad_96_wellplate_200ul_pcr', slot, 'output plate'))
            else:  # Si no se usan 2 output_plates, se explicita eso con un None
                output_plates2.append(None)
    # print("output_plates1 : ", output_plates1)
    # print("output_plates2 : ", output_plates2)

    # Importamos Eppendorf tube rack
    eppendorf_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 9, 'eppendorf rack')

    eppendorf_control_positivo = eppendorf_rack.wells()[0]  # A1 del tuberack; esquina superior izquierda
    eppendorf_control_negativo = eppendorf_rack.wells()[3]  # D1 del tuberack; esquina inferior izquierda

    # Import INSTRUMENTS:
    m20 = protocol.load_instrument('p20_multi_gen2', 'right', tip_racks=tipracks)
    s20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=tipracks)

    # COMMANDS
    protocol.comment("\nCOMPLETE COLUMNS :")

    m20.well_bottom_clearance.aspirate = 0.6
    m20.well_bottom_clearance.dispense = 0.6

    # Calculo cuantas columnas completas contienen mis sample_plate (s): una lista con las columnas completas del sample_plate
    s_plates_cmplt_cols = []
    for number, s_plate in zip(sample_number, sample_plates):
        # Lista con las columnas completas del sample_plate
        s_plates_cmplt_cols.append(s_plate.rows()[0][:divmod(number, 8)[0]])
    # print("\ns_plates_cmplt_cols : ", s_plates_cmplt_cols)

    # Creo una lista que contendrá las columnas completas para el output_plate1 y 2
    o_plates_cmplt_cols_rep1 = []
    o_plates_cmplt_cols_rep2 = []

    # Reviso cada sample_plate y checkeo si hay 1 o 2 output_plates asociadas:
    for number, o_plate1, o_plate2 in zip(sample_number, output_plates1, output_plates2):
        if o_plate2 is None:  # Esa sample_plate tiene sólo 1 output_plate asociada (tiene 46 muestras o menos)
            # una lista de columnas del output_plate1 con una cantidad de columnas igual a la cantidad de columnas completas en el sample_plate que inicie desde la columna 1
            o_plates_cmplt_cols_rep1.append(o_plate1.rows()[0][:divmod(number, 8)[0]])
            # una lista de columnas del output_plate1 con una cantidad de columnas igual a la cantidad de columnas completas en el sample_plate que inicie desde la columna 6
            o_plates_cmplt_cols_rep2.append(o_plate1.rows()[0][6:6 + divmod(number, 8)[0]])

        if o_plate2 is not None:  # Esa sample_plate tiene 2 output_plates asociadas (tiene 46 muestras o más)
            # una lista de columnas del output_plate1 y output_plate2 con una cantidad de columnas igual a la cantidad de columnas completas en el sample_plate que inicie desde la columna 1
            o_plates_cmplt_cols_rep1.append(o_plate1.rows()[0][:divmod(number, 8)[0]])
            # una lista de columnas del output_plate1 y output_plate2 con una cantidad de columnas igual a la cantidad de columnas completas en el sample_plate que inicie desde la columna 6
            o_plates_cmplt_cols_rep2.append(o_plate2.rows()[0][:divmod(number, 8)[0]])
            # print("\no_plates_cmplt_cols_rep1 : ", o_plates_cmplt_cols_rep1)
    # print("\no_plates_cmplt_cols_rep2 : ", o_plates_cmplt_cols_rep2)

    # Creo una lista que contendrá las columnas del tiprack que van a servir para traspasar las columnas completas del sample_plate a las output_plates
    tips_cmplt_cols = []
    for rack, numero in zip(tipracks, sample_number):
        tips_cmplt_cols.append(rack.rows()[0][:divmod(numero, 8)[0]])
    # print("\ntips_cmplt_cols : ", tips_cmplt_cols)

    # Traspasamos las muestras del sample_plate al outputplate usando las tips. Esto se hace tomando la columna X de las tips y traspasando el contenido de la columna X del sample_plate a la columna X del (de los) output_plate (s). Eso se hace usando la función zip().
    template_volume = 1
    for sample_sublist, output1_sublist, output2_sublist, tip_sublist in zip(s_plates_cmplt_cols,
                                                                             o_plates_cmplt_cols_rep1,
                                                                             o_plates_cmplt_cols_rep2, tips_cmplt_cols):
        for sample_col, output1_col, output2_col, tip_col in zip(sample_sublist, output1_sublist, output2_sublist,
                                                                 tip_sublist):
            # Paso de muestras desde el sample_plate a la primera replica de las output_plates
            m20.pick_up_tip(tip_col)
            m20.mix(2, 10, sample_col)
            m20.aspirate(template_volume * 2,
                         sample_col)  # Tomamos el doble del volumen de templado que se necesita, para luego hacer una réplica técnica dividiendo el volumen total a la mitad
            m20.dispense(m20.current_volume, output1_col)
            m20.mix(5, 20, output1_col)
            # Desde una columna completa de un output_plate se pasa a otra columna completa que tendrá la réplica técnica
            m20.aspirate(15, output1_col)
            m20.dispense(m20.current_volume, output2_col)
            m20.blow_out(output2_col.top(z=-1))
            m20.touch_tip(v_offset=-1, speed=50)
            m20.drop_tip()

    protocol.comment("\nINCOMPLETE COLUMNS :")

    m20.well_bottom_clearance.aspirate = 0.6
    m20.well_bottom_clearance.dispense = 0.6

    # Determino dónde está (si es que existe) la columna incompleta de mi sample_plate y lo guardo en una lista
    s_plates_incmplt_cols = []
    for number, s_plate in zip(sample_number, sample_plates):
        # Lista con las columnas completas del sample_plate
        s_plates_incmplt_cols.append(s_plate.rows()[0][divmod(number, 8)[0]:divmod(number, 8)[0] + 1])
    # print("\ns_plates_incmplt_cols : ", s_plates_incmplt_cols)

    # Determino dónde está (si es que existe) la(s) columna(s) incompleta(s) de mi output_plates, para las replicas 1 y 2.
    o_plates_incmplt_cols_rep1 = []
    o_plates_incmplt_cols_rep2 = []

    # Determino dónde estarán las primeras y segundas réplicas de la reacción:
    for number, o_plate1, o_plate2 in zip(sample_number, output_plates1, output_plates2):
        # Si el sample_plate tiene 46 muestras o menos, entonces tiene sólo un output_plate asociado, por lo que las réplicas son mitades de placa
        if o_plate2 is None:  # Esa placa tiene sólo 1 output_plate asociada (tiene 46 muestras o menos)
            # una lista de columnas del output_plate1 con una cantidad de columnas igual a la cantidad de columnas completas en el sample_plate que inicie desde la columna 1
            o_plates_incmplt_cols_rep1.append(o_plate1.rows()[0][divmod(number, 8)[0]:divmod(number, 8)[0] + 1])
            # una lista de columnas del output_plate1 con una cantidad de columnas igual a la cantidad de columnas completas en el sample_plate que inicie desde la columna 6
            o_plates_incmplt_cols_rep2.append(o_plate1.rows()[0][6 + divmod(number, 8)[0]:6 + divmod(number, 8)[
                0] + 1])  # El +6 es porque estas replicas están en la segunda mitad de la placa

        # Si el sample_plate tiene más de 46 muestras, entonces tiene 2 output_plates asociadas, por lo que las réplicas se encuentran en 2 placas distintas
        if o_plate2 is not None:  # Esa placa tiene 2 output_plates asociadas (tiene 46 muestras o más)
            # una lista de columnas del output_plate1 y output_plate2 con una cantidad de columnas igual a la cantidad de columnas completas en el sample_plate que inicie desde la columna 1
            o_plates_incmplt_cols_rep1.append(o_plate1.rows()[0][divmod(number, 8)[0]:divmod(number, 8)[0] + 1])
            # una lista de columnas del output_plate1 y output_plate2 con una cantidad de columnas igual a la cantidad de columnas completas en el sample_plate que inicie desde la columna 6
            o_plates_incmplt_cols_rep2.append(o_plate2.rows()[0][divmod(number, 8)[0]:divmod(number, 8)[0] + 1])
            # print("\no_plates_incmplt_cols_rep1 : ", o_plates_incmplt_cols_rep1)
    # print("\no_plates_incmplt_cols_rep2 : ", o_plates_incmplt_cols_rep2)

    # Creo una lista que contendrá las columnas del tiprack que van a traspasar las columnas incompletas del sample_plate a las output_plates
    tips_incmplt_cols = []
    for rack, numero in zip(tipracks, sample_number):
        # divmod(numero,8)[0] = número de columnas completas
        # divmod(numero,8)[1] = número de wells que contienen muestras dentro de la columna incompleta
        if divmod(numero, 8)[1] != 0:  # Si hay alguna columna incompleta
            tips_incmplt_cols.append(
                [subelement for element in rack.columns()[divmod(numero, 8)[0]:divmod(numero, 8)[0] + 1] for subelement
                 in element][8 - divmod(numero, 8)[1]])

        else:  # Entonces todas las columnas están completas
            tips_incmplt_cols.append(None)
            # Es importante explicitar si no hay columnas incompletas, puesto que esta parte me va a permitir que luego el script decida si debe hacer el traspaso de columnas incompletas o no
    # print("\ntips_incmplt_cols : ", tips_incmplt_cols)

    # OJO: LA PIPETA USA UNA CANTIDAD DE CORRIENTE PARA HACER EL PICK_UP, QUE ES DEPENDE DE LA CANTIAD DE PUNTAS QUE SE VAN A TOMAR.
    # SI QUEREMOS HACER UN PICK_UP DE MENOS DE 8 TIPS, DEBEMOS DECIRLE QUE USE MENOS CORRIENTE, PARA QUE LA FUERZA APLICADA SOBRE EL TIPRACK SEA LA APROPIADA.
    # PARA ESO DECLARAMOS EL SIGUIENTE VALOR:
    per_tip_pickup_current = .075  # 0.075 es lo que usa la p20 para cada tip tomado, mientras que la p300 usa 0.1 por tip.

    for number_of_samples, sample_sublist, output1_sublist, output2_sublist, tip_col in zip(sample_number,
                                                                                            s_plates_incmplt_cols,
                                                                                            o_plates_incmplt_cols_rep1,
                                                                                            o_plates_incmplt_cols_rep2,
                                                                                            tips_incmplt_cols):
        for sample_col, output1_col, output2_col in zip(sample_sublist, output1_sublist, output2_sublist):

            if tip_col is not None:  # Este código se va a ejecutar SÓLO si hay columnas incompletas. Esto lo sabrá porque en el tips_incmplt_cols dijimos si habían columnas incompletas o no

                # Con esta parte le decimos que para tomar menos de 8 muestras, usará una cantidad de corriente igual al valor de corriente por tip (que depende de la pipeta) * el número de tips
                pick_up_current = per_tip_pickup_current * divmod(number_of_samples, 8)[1]
                # print("current : ", pick_up_current, "| samples : ", divmod(number_of_samples, 8)[1]) # Con esta línea se puede chequear que está usando valores de corriente distintos en cada toma

                protocol._implementation._hw_manager.hardware._attached_instruments[
                    m20._implementation.get_mount()
                ].update_config_item('pick_up_current', pick_up_current)

                # Toma template desde el sample_plate y lo lleva a la primera réplica (esto lo hace con menos de 8 puntas).
                m20.pick_up_tip(tip_col)
                m20.mix(2, 10, sample_col)
                m20.aspirate(template_volume * 2, sample_col)
                m20.dispense(m20.current_volume, output1_col)
                m20.mix(5, 20, output1_col)
                # Desde una columna incompleta de un output_plate se pasa a otra columna incompleta que tendrá la réplica técnica
                m20.aspirate(15, output1_col)
                m20.dispense(m20.current_volume, output2_col)
                m20.blow_out(output2_col.top(z=-1))
                m20.touch_tip(v_offset=-1, speed=50)
                m20.drop_tip()

    protocol.comment("\nPOSITIVE CONTROL :")
    output_wells_control_positivo_rep1 = []
    output_wells_control_positivo_rep2 = []

    # Creamos las listas con las posiciones de los controles positivos
    for number, o_plate1, o_plate2 in zip(sample_number, output_plates1, output_plates2):
        if o_plate2 is None:
            # Los controles se encuentran en la misma placa. Uno va justo después de las muestras y el otro va 46 wells después
            output_wells_control_positivo_rep1.append(o_plate1.wells()[number])
            output_wells_control_positivo_rep2.append(o_plate1.wells()[
                                                          number + 48])  # +48 porque tiene que estar en la segunda mitad (luego de los primeros 48 pocillos)
        if o_plate2 is not None:
            # Los controles se encuentran en 2 placas distintas. Ambos van justo después de la cantidad de muestras.
            output_wells_control_positivo_rep1.append(o_plate1.wells()[number])
            output_wells_control_positivo_rep2.append(o_plate2.wells()[number])

    s20.pick_up_tip()
    s20.mix(5, 10, eppendorf_control_positivo)

    for well_ctrl_positivo_rep1, well_ctrl_positivo_rep2 in zip(output_wells_control_positivo_rep1,
                                                                output_wells_control_positivo_rep2):
        if not s20.has_tip:
            s20.pick_up_tip()
        s20.aspirate(template_volume * 2, eppendorf_control_positivo)
        s20.dispense(s20.current_volume, well_ctrl_positivo_rep1)
        s20.mix(5, 20, well_ctrl_positivo_rep1)
        s20.aspirate(15, well_ctrl_positivo_rep1)
        s20.dispense(s20.current_volume, well_ctrl_positivo_rep2)
        s20.blow_out(well_ctrl_positivo_rep2.top(z=-1))
        s20.touch_tip(v_offset=-1, speed=50)
        s20.drop_tip()
    # print("output_wells_control_positivo_rep1 : ", output_wells_control_positivo_rep1)
    # print("output_wells_control_positivo_rep2 : ", output_wells_control_positivo_rep2)

    protocol.comment("\nNEGATIVE CONTROL :")
    output_wells_control_negativo_rep1 = []
    output_wells_control_negativo_rep2 = []

    # Creamos las listas con las posiciones de los controles positivos
    for number, o_plate1, o_plate2 in zip(sample_number, output_plates1, output_plates2):
        if o_plate2 is None:
            # Los controles se encuentran en la misma placa. Uno va justo después de las muestras y el otro va 48 wells después
            output_wells_control_negativo_rep1.append(o_plate1.wells()[number + 1])
            output_wells_control_negativo_rep2.append(o_plate1.wells()[
                                                          number + 48 + 1])  # +48 porque tiene que estar en la segunda mitad (luego de los primeros 48 pocillos)
        if o_plate2 is not None:
            # Los controles se encuentran en 2 placas distintas. Ambos van justo después de la cantidad de muestras.
            output_wells_control_negativo_rep1.append(o_plate1.wells()[number + 1])
            output_wells_control_negativo_rep2.append(o_plate2.wells()[number + 1])

    s20.pick_up_tip()
    s20.mix(5, 10, eppendorf_control_negativo)

    for well_ctrl_negativo_rep1, well_ctrl_negativo_rep2 in zip(output_wells_control_negativo_rep1,
                                                                output_wells_control_negativo_rep2):
        if not s20.has_tip:
            s20.pick_up_tip()
        s20.aspirate(template_volume * 2, eppendorf_control_negativo)
        s20.dispense(s20.current_volume, well_ctrl_negativo_rep1)
        s20.mix(5, 20, well_ctrl_negativo_rep1)
        s20.aspirate(15, well_ctrl_negativo_rep1)
        s20.dispense(s20.current_volume, well_ctrl_negativo_rep2)
        s20.blow_out(well_ctrl_negativo_rep2.top(z=-1))
        s20.touch_tip(v_offset=-1, speed=50)
        s20.drop_tip()
    # print("output_wells_control_positivo_rep1 : ", output_wells_control_positivo_rep1)
    # print("output_wells_control_positivo_rep2 : ", output_wells_control_positivo_rep2)