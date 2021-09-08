from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'PCR protocol',
    'author': 'B.Valderrama',
    'description': 'First iteration. Primers: CVA, ACLSV, CNRMV',
    'apiLevel': '2.10'
}


def run(protocol: protocol_api.ProtocolContext):
    
    ## Labware
    # Tips
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', '9')
    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', '6')
    
    # Wells
    reactives = protocol.load_labware('biorad_96_wellplate_200ul_pcr', '8') 
    output = protocol.load_labware('biorad_96_wellplate_200ul_pcr', '5')
    
    
    ## Instruments
    p300 = protocol.load_instrument('p300_multi_gen2', 'left', tip_racks = [tiprack_300])
    p20 =  protocol.load_instrument('p20_multi_gen2', 'right', tip_racks = [tiprack_20])
    
    
    ## Number of samples and Volumes are defined
    samples = 6
    
    # Volume Master mix
    MM = 25 # per well  
    MM_total = 25 * samples # Total to use
    
    # Volume DNA
    DNA = 2
    DNA_total = 2*(samples/2)
    
    # Volume H20
    H20_sample = 21 # 3 wells
    H20_ctrl = 23 # 3 wells
    H20_total = H20_sample*(samples/2) + H20_ctrl*(samples/2)
    
    # Volumes Primers
    CVA = 2
    CVA_total = 2*(samples/3)
    
    ACLSV = 2
    ACLSV_total = 2*(samples/3)
    
    CNRMV = 2
    CNRMV_total = 2*(samples/3)
    
    
    ## Commands
    ## Transporting reactives
    
    # Master Mix from reactives to output
    p300.pick_up_tip()
    p300.aspirate(MM_total, reactives['A1'])
    for i in range(6):
        p300.dispense(MM, output['A'+str(i+1)])
    p300.drop_tip()
    
    # H20 from reactives to output
    p300.pick_up_tip()
    p300.aspirate(H20_total, reactives['A2'])
    for i in range(6):
        if (i+1) % 2 != 0: # Positivos
            p300.dispense(H20_sample, output['A'+str(i+1)])
        else: # Controls
            p300.dispense(H20_ctrl, output['A'+str(i+1)])
    p300.drop_tip()
    
    # DNA from reactives to output (avoiding negative controls)
    p20.pick_up_tip()
    p20.aspirate(DNA_total, reactives['A3'])
    for i in range(6):
        if (i+1) % 2 != 0: # Positivo
            p20.dispense(DNA, output['A'+str(i+1)])
    p20.drop_tip()
    
    # CVA from reactives to output (just the ones in which it must be used)
    p20.pick_up_tip()
    p20.aspirate(CVA_total, reactives['A4'])
    for i in [2,1]: # First we dispense the primer within the negative control and then in the well with the sample
        p20.dispense(CVA, output['A'+str(i)])
    p20.drop_tip()
    
    # ACLSV
    p20.pick_up_tip()
    p20.aspirate(ACLSV_total, reactives['A5'])
    for i in [4,3]:
        p20.dispense(ACLSV, output['A'+str(i)])
    p20.drop_tip()
    
    #CNRMV
    p20.pick_up_tip()
    p20.aspirate(CNRMV_total, reactives['A6'])
    for i in [6,5]:
        p20.dispense(CNRMV, output['A'+str(i)])
    p20.drop_tip()
