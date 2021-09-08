from opentrons import protocol_api
#from opentrons import simualte #opentrons_simulate.exe my_protocol.py

## Metadata
metadata = {
    'protocolName': 'Moving tips within a rack',
    'author': 'B. Valderrama>',
    'description': 'Learning how to move the tips of a rack using specific positions and for-loops',
    'apiLevel': '2.10'
}

## Protocol run
def run(protocol: protocol_api.ProtocolContext):

    ## Labware
#    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', '6')
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', '4')
    

    ## Pipette
#    pipette_20 = protocol.load_instrument('p20_multi_gen2', 'right', tip_racks = [tiprack_20])
    pipette_300 = protocol.load_instrument('p300_multi_gen2', 'left', tip_racks = [tiprack_300])

    ## Commands

    # It will pick the first line of p20 tips and then it will return it to the same position
#    pipette_20.pick_up_tip()
#    pipette_20.return_tip() # Tips are returned to the same position. We must use drop_tip to change the place as follows...


    # It will pick the first column of p20 tips and then it will return it to the second column of the rack
#    pipette_20.pick_up_tip(tiprack_20['A1']) # NOTE: It won't use tips if they were already used in the same protocol, so we need to state it
#    pipette_20.drop_tip(tiprack_20['A2']) # We need to state where we will drop the tips. If not, it will drop them on the trash


    # It will pick the last column of p20 tips and then it will return it to the first column of the rack
#    pipette_300.pick_up_tip(tiprack_300['A12'])
#    pipette_300.drop_tip(tiprack_300['A1'])


    # Tranposrt the same line of tips across all the columns of the rack
    # loop over the 12 columns of the rack
    for i in range(12):
        # i = 10 it means we will drop the tips on the last column of the rack, so we don't go further
        if i <= 10 :
            pipette_300.pick_up_tip(tiprack_300['A'+str(i+1)])
            pipette_300.drop_tip(tiprack_300['A'+str(i+2)])
