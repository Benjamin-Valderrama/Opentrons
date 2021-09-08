from opentrons import protocol_api
#from opentrons import simualte #opentrons_simulate.exe my_protocol.py

## Metadata
metadata = {
    'protocolName': 'Creating Green',
    'author': 'B. Valderrama>',
    'description': 'Mixing water with dyers to make green',
    'apiLevel': '2.10'
}

## Protocol run
def run(protocol: protocol_api.ProtocolContext):

    ## Labware
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '6')
    palette = protocol.load_labware('nest_12_reservoir_15ml', '5')


    ## Pipette
    pipette = protocol.load_instrument('p20_multi_gen2', 'right', tip_racks = [tiprack])


    ## Commands

    ## It will create 3 greens slots of different concentration of yellow between them

    #Picking yellow
    pipette.pick_up_tip()

    pipette.aspirate(12, palette['A1'])

    pipette.air_gap(5)
    
    pipette.dispense(6, palette['A10'])
    pipette.dispense(4, palette['A11'])
    pipette.dispense(2, palette['A12'])

    pipette.drop_tip()


    #Picking blue
    pipette.pick_up_tip()
    
    pipette.aspirate(9, palette['A3']) 

    pipette.air_gap(5)

    pipette.dispense(3, palette['A10'])
    pipette.dispense(3, palette['A11'])
    pipette.dispense(3, palette['A12'])


    # Mixing slots
    pipette.mix(4, 3, palette['A12'])
    pipette.mix(4, 3, palette['A11'])
    pipette.mix(4, 3, palette['A10'])

    pipette.drop_tip()
