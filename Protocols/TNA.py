## Test this protocolo using only 8 samples.

## VOLUMEN De Muestra: 50 µL
## VOLUMEN de Elusion: 50 µL


import math
import json
from opentrons import types


def get_values(*names):
    # Here you must change the values to meet your needs
    _all_values = json.loads(
        """{"mag_mod":"magnetic module gen2", "pipette_type":"p300_multi_gen2","pipette_mount":"right","sample_number":48,"sample_volume":75,"bead_ratio":1,"elution_buffer_volume":50,"incubation_time":7,"settling_time":7,"drying_time":5,"custom_tiprack":"no", "custom_output_plate":"no"}""")
    return [_all_values[n] for n in names]


metadata = {
    'protocolName': 'TNA extraction',
    'author': 'Multiplex <bvalderrama@multiplex.bio>',
    'description': 'Total nucleic acid extraction with 96 samples and a timer printed on screen for each incubation time',
    'source': 'Modified from Protocol Library',
    'apiLevel': '2.11'
}


def run(protocol_context):
    [mag_mod, pipette_type, pipette_mount, sample_number, sample_volume,
     bead_ratio, elution_buffer_volume, incubation_time, settling_time,
     drying_time, custom_tiprack, custom_output_plate] = get_values(
        "mag_mod", "pipette_type", "pipette_mount", "sample_number",
        "sample_volume", "bead_ratio", "elution_buffer_volume",
        "incubation_time", "settling_time", "drying_time",
        "custom_tiprack", "custom_output_plate"
    )

    ## Modules
    mag_deck = protocol_context.load_module(mag_mod, '1')
    mag_plate = mag_deck.load_labware('biorad_96_wellplate_200ul_pcr')

    ## Labware
    if custom_output_plate == "yes":
        output_plate = protocol_context.load_labware('nest_96_wellplate_200ul_cap', '2', 'output plate')
    else:
        output_plate = protocol_context.load_labware('biorad_96_wellplate_200ul_pcr', '2', 'output plate')

    # Number (and position) of tipracks
    total_tips = sample_number * 8
    tiprack_num = math.ceil(total_tips / 96)
    slots = ['3', '5', '6', '7', '8', '9', '10', '11'][:tiprack_num]

    ## Instruments
    # Pipette selection
    pip_range = pipette_type.split('_')[0]
    if pip_range == 'p1000':
        tip_name = 'opentrons_96_tiprack_1000ul'
    elif pip_range == 'p300' or pip_range == 'p50':
        tip_name = 'opentrons_96_tiprack_300ul'
    elif pip_range == 'p20':
        tip_name = 'opentrons_96_tiprack_20ul'
    else:
        tip_name = 'opentrons_96_tiprack_10ul'

    # Defining tipracks based whether they are custom or not
    if custom_tiprack == "yes":
        tipracks = [protocol_context.load_labware('vertex_96_tiprack_200ul', slot) for slot in slots]
    else:
        tipracks = [protocol_context.load_labware(tip_name, slot) for slot in slots]

    # Pipette load
    pipette = protocol_context.load_instrument(pipette_type, pipette_mount, tip_racks=tipracks)
    mode = pipette_type.split('_')[1]

    ## Labware
    # Defining containers for reagents depending on the total number of samples
    if mode == 'single':
        if sample_number <= 5:
            reagent_container = protocol_context.load_labware(
                'opentrons_24_tuberack_nest_2ml_snapcap', '4')
            liquid_waste = protocol_context.load_labware(
                'usascientific_12_reservoir_22ml', '5').wells()[-1]
        else:
            reagent_container = protocol_context.load_labware(
                'usascientific_12_reservoir_22ml', '4')
            liquid_waste = reagent_container.wells()[-1]
        samples = [well for well in mag_plate.wells()[:sample_number]]
        output = [well for well in output_plate.wells()[:sample_number]]
    else:
        reagent_container = protocol_context.load_labware(
            'usascientific_12_reservoir_22ml', '4')
        # Many liquid waste wells due to the great amount of liquid used on each wash
        liquid_waste1 = reagent_container.wells()[-1]
        liquid_waste2 = reagent_container.wells()[-2]
        liquid_waste3 = reagent_container.wells()[-3]
        liquid_waste4 = reagent_container.wells()[-4]

        col_num = math.ceil(sample_number / 8)
        samples = [col for col in mag_plate.rows()[0][:col_num]]
        output = [col for col in output_plate.rows()[0][:col_num]]

    ## Labware
    # Define the internal structure of the reagents containers
    beads = reagent_container.wells()[0]
    ethanol = reagent_container.wells()[1]
    ethanol2 = reagent_container.wells()[2]
    ethanol_salt = reagent_container.wells()[3]
    elution_buffer = reagent_container.wells()[4]

    # Defining bead and mix volume
    bead_volume = sample_volume * bead_ratio  # bead_volume = 75 * 1

    if bead_volume < 30:
        bead_volume = 30

    mix_vol = 30
    total_vol = bead_volume + sample_volume + 5

    if (bead_volume > pipette.max_volume) or (mix_vol > pipette.max_volume) or (total_vol > pipette.max_volume):
        print("Some volume is higher than max pipette volume ")
        quit()

    ## Defining default values for pipetting behavior
    # Mix beads and PCR samples
    pipette.flow_rate.aspirate = 30
    pipette.flow_rate.dispense = 300
    pipette.well_bottom_clearance.aspirate = 1
    pipette.well_bottom_clearance.dispense = 5
    air_vol = pipette.max_volume * 0.1

    ## The protocol begins:
    # Mix the beads and dispense them to sample
    for target in samples:
        pipette.pick_up_tip()
        pipette.mix(10, 50, beads)
        pipette.transfer(bead_volume, beads, target, new_tip='never')
        pipette.mix(20, 50, target)
        pipette.air_gap(air_vol)  # || Para evitar derramar líquido sobre el deck o labware
        pipette.drop_tip()

    # Incubate sample with beads at RT for 7 minutes
    for i in range(incubation_time):
        protocol_context.delay(minutes=1,
                               msg='{} minutes passed out of a total of {} minutes'.format(i, incubation_time))

    # Engagae MagDeck and incubate
    mag_deck.engage(height=10)

    # Incubation time with iman for 7 mins
    for i in range(settling_time):
        protocol_context.delay(minutes=1, msg='{} minutes passed out of a total of {} minutes'.format(i, settling_time))

    # Remove supernatant from magnetic beads (total_vol = 50 uL from sample + 50 uL from beads + 5 extra uL)
    pipette.flow_rate.aspirate = 10
    pipette.flow_rate.dispense = 150

    for target in samples:
        pipette.pick_up_tip()
        pipette.aspirate(total_vol, target)
        pipette.air_gap(air_vol)
        pipette.dispense(total_vol, liquid_waste1.top())
        pipette.flow_rate.blow_out = 15
        pipette.blow_out(liquid_waste1.top(z=-1))
        wall_location = (liquid_waste1.length / 2)
        pipette.move_to(liquid_waste1.top().move(types.Point(x=wall_location, y=0, z=-1)))
        pipette.move_to(liquid_waste1.top().move(types.Point(x=-wall_location, y=0, z=-1)))
        pipette.drop_tip()

        # First wash: 150 uL of Ethanol salt (70% ethanol and CaCl2 0.5M)
    # NOTE: All washing steps and the drying steps are done with the iman
    pipette.flow_rate.aspirate = 25
    pipette.flow_rate.dispense = 30

    # \ Try using same tip for all
    #### \ Maybe at this point do mixing per tip usage......
    mag_deck.disengage()
    for target in samples:
        # Slowly aspiration of the ethanol salt for a correct pipetting
        pipette.flow_rate.aspirate = 25
        pipette.flow_rate.dispense = 30
        pipette.pick_up_tip()
        pipette.aspirate(150, ethanol_salt)
        protocol_context.delay(seconds=1)
        pipette.move_to(ethanol_salt.top(), speed=20)
        pipette.air_gap(air_vol)

        # || This instructions will allow the pipette to move towards well's wall so it can dispense liquids with high adhesion with its help
        # center_location = target.center()
        # wall_location= target.diameter()/2
        # adjusted_location=center_location.move(types.Point(x=wall_location, y=0, z=0))
        # pipette.move_to(adjusted_location)

        # Rapid mix to allow disgregation of the beads
        pipette.flow_rate.aspirate = 150
        pipette.flow_rate.dispense = 150
        pipette.dispense(pipette.current_volume, target.top())
        pipette.mix(20, 100, target)
        pipette.move_to(target.top(), speed=20)
        protocol_context.delay(seconds=1)
        pipette.flow_rate.blow_out = 15
        pipette.blow_out(target.top(z=-0.5))
        pipette.touch_tip(target, v_offset=-0.5, speed=50)

        pipette.drop_tip()

    mag_deck.engage(height=10)

    # Incubation with Ethanol salt and the iman for 5 minutes
    for i in range(5):
        protocol_context.delay(minutes=1, msg='{} minutes passed out of a total of {} minutes'.format(i, 5))

    # Remove first wash (70% ethanol NaCl 5 M)
    ## || All removals are done with the same tip
    pipette.pick_up_tip()
    for target in samples:
        pipette.aspirate(150, target)
        pipette.move_to(target.top(), speed=20)
        pipette.air_gap(air_vol)
        pipette.flow_rate.dispense = 30
        pipette.dispense(pipette.current_volume,
                         liquid_waste2.top())  # || It could be a good idea to dispense on the wall of the well
        pipette.flow_rate.blow_out = 15
        pipette.blow_out(liquid_waste2.top(z=-0.5))
        # my_own_touch_tips:
        wall_location = (liquid_waste2.length / 2)
        pipette.move_to(liquid_waste2.top().move(types.Point(x=wall_location, y=0, z=-0.5)))
        pipette.move_to(liquid_waste2.top().move(types.Point(x=-wall_location, y=0, z=-0.5)))
    pipette.drop_tip()

    # Second wash: 150 uL of Ethanol (70% ethanol)
    ## || All washes and removals are done with the same tip
    pipette.flow_rate.aspirate = 25
    pipette.flow_rate.dispense = 150

    pipette.pick_up_tip()
    for target in samples:
        # Slowly aspirate the ethanol
        pipette.aspirate(150, ethanol)
        protocol_context.delay(seconds=1)
        pipette.move_to(ethanol.top(), speed=20)
        pipette.air_gap(air_vol)

        # Slowly dispense the ethanol
        # center_location = target.center()
        # wall_location= target.diameter()/2
        # adjusted_location=center_location.move(types.Point(x=wall_location, y=0, z=0))
        # pipette.move_to(adjusted_location)

        pipette.move_to(target.top())
        pipette.dispense(pipette.current_volume)
        protocol_context.delay(seconds=1)
        pipette.flow_rate.blow_out = 15
        pipette.blow_out(target.top(z=-0.5))
        pipette.touch_tip(target, v_offset=-0.5, speed=50)
        pipette.move_to(target.top())

    # Incubation with Ethanol 70% for 1 minute
    protocol_context.delay(minutes=1)

    # Remove second wash (70% ethanol)
    for target in samples:
        pipette.aspirate(150, target)
        pipette.move_to(target.top(), speed=20)
        pipette.air_gap(air_vol)
        # pipette.flow_rate.dispense = 30
        pipette.dispense(pipette.current_volume,
                         liquid_waste3.top())  # || It could be a good idea to dispense on the wall of the well
        pipette.flow_rate.blow_out = 15
        pipette.blow_out(liquid_waste3.top(z=-0.5))
        # my_own_touch_tips
        wall_location = (liquid_waste3.length / 2)
        pipette.move_to(liquid_waste3.top().move(types.Point(x=wall_location, y=0, z=-0.5)))
        pipette.move_to(liquid_waste3.top().move(types.Point(x=-wall_location, y=0, z=-0.5)))
    pipette.drop_tip()

    # Third wash: 150 uL of Ethanol (70% Ethanol)
    ##\ Try using same tip for all
    pipette.flow_rate.aspirate = 25
    pipette.flow_rate.dispense = 150

    pipette.pick_up_tip()
    for target in samples:
        # Slowly aspirate the ethanol
        pipette.aspirate(150, ethanol2)
        protocol_context.delay(seconds=1)
        pipette.move_to(ethanol2.top(), speed=20)
        pipette.air_gap(air_vol)

        # Slowly dispense the ethanol
        # center_location = target.center()
        # wall_location= target.diameter()/2
        # adjusted_location=center_location.move(types.Point(x=wall_location, y=0, z=0))
        # pipette.move_to(adjusted_location)

        pipette.move_to(target.top())
        pipette.dispense(pipette.current_volume)
        protocol_context.delay(seconds=1)
        pipette.flow_rate.blow_out = 15
        pipette.blow_out(target.top(z=-0.5))
        pipette.touch_tip(target, v_offset=-0.5, speed=50)
        pipette.move_to(target.top())

    # Incubation with Ethanol 70% for 1 minute
    protocol_context.delay(minutes=1)

    # Carefully remove 70% ethanol
    ###\ I see ethanol sticking and falling on tip and on plate / reduce air volume? # || I think this was solved
    pipette.flow_rate.aspirate = 15  # aspirate slower than previous steps
    pipette.flow_rate.dispense = 30
    pipette.well_bottom_clearance.aspirate = 1

    for target in samples:
        pipette.aspirate(150, target)
        pipette.move_to(target.top(), speed=20)
        pipette.air_gap(air_vol)
        pipette.dispense(pipette.current_volume,
                         liquid_waste4.top())  # || It could be a good idea to dispense on the wall of the well
        pipette.flow_rate.blow_out = 15
        pipette.blow_out(liquid_waste4.top(z=-0.5))
        # pipette.touch_tip(liquid_waste4.top(z=-0.5))
        wall_location = (liquid_waste4.length / 2)
        pipette.move_to(liquid_waste4.top().move(types.Point(x=wall_location, y=0, z=-0.5)))
        pipette.move_to(liquid_waste4.top().move(types.Point(x=-wall_location, y=0, z=-0.5)))

        # || Quizás agregar otro paso de sacar unos 30uL desde target hasta el liquid waste 4

    pipette.drop_tip()

    # Dry at RT for 5 minutes
    for i in range(drying_time):
        protocol_context.delay(minutes=1, msg='{} minutes passed out of a total of {} minutes'.format(i, drying_time))

    # Disengage MagDeck
    mag_deck.disengage()

    # Elution with 40 uL of elution buffer (ultra pure H2O) and then apply a strong mix
    pipette.flow_rate.aspirate = 50
    pipette.flow_rate.dispense = 300
    for target in samples:
        pipette.pick_up_tip()
        pipette.transfer(elution_buffer_volume + 5, elution_buffer, target, new_tip='never')
        pipette.mix(20, mix_vol, target)
        pipette.blow_out(target.top(z=-1))
        pipette.drop_tip()

    # Incubation at RT for 5 minutes
    for i in range(5):
        protocol_context.delay(minutes=1, msg='{} minutes passed out of a total of {} minutes'.format(i, 5))

    # Incubation with iman for 7 minutes
    mag_deck.engage(height=10)

    for i in range(settling_time):
        protocol_context.delay(minutes=1, msg='{} minutes passed out of a total of {} minutes'.format(i, settling_time))

    # Transfer 53 uL of PCR product to a new well
    pipette.flow_rate.aspirate = 10
    pipette.well_bottom_clearance.aspirate = 1.5
    for target, dest in zip(samples, output):
        pipette.pick_up_tip()
        pipette.aspirate(elution_buffer_volume, target)
        pipette.dispense(pipette.current_volume, dest)
        pipette.blow_out(dest.top(z=-0.5))
        pipette.touch_tip(dest, v_offset=-0.5, speed=50)
        pipette.drop_tip()