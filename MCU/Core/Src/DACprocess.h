/*
 * DACprocess.h
 *
 *  Created on: Jan 14, 2025
 *      Author: Timothy
 */

#ifndef SRC_DACPROCESS_H_
#define SRC_DACPROCESS_H_

#include <stdint.h>

#define AWG_SAMPLES (1024 * 4)
#define AWG_NUM_CHAN 2
#define MAGIC_NUM 0x42
#define HS_STRING_LEN 4
#define ACK_STRING_LEN 8

#define PACK __attribute__((packed))

extern uint8_t awg_lut[AWG_NUM_CHAN][AWG_SAMPLES*2];

typedef struct {
    uint8_t packet_type;
    union {
        struct { // packet_type = 0
            uint8_t handshake_string[HS_STRING_LEN];
        } PACK HandShake;
        struct { // packet_type = 1
            uint8_t channel;
            uint8_t gain;
            //uint8_t temp;
            uint16_t PSC;
            uint16_t ARR;
            uint16_t CCR_offset;
            uint16_t numSamples;
            uint16_t phaseARR;
        } PACK AWG_SET;

        struct { // packet_type = 2
            uint8_t channel;
            uint8_t adcmode;
            uint8_t triggermode;
            uint16_t triggerval;
            uint8_t sampletime;
            uint8_t offset;
            uint8_t attenuation;
            uint8_t amp10;
            uint8_t amp5;
            uint8_t amp2_5;
            uint8_t amp1;
        } PACK ADC_SET;
        struct { // packet_type = 3
            uint8_t control;
            uint16_t triggerpin;
            uint16_t triggeredge;
            uint16_t period16;
			uint16_t prescaler;
            uint32_t period32;
        } PACK LOGIC_SET;


    } PACK Content;
} PACK RECV_Packet;

typedef struct PACK {
    uint8_t packet_type;
    uint8_t ack_string[ACK_STRING_LEN];
    uint8_t whitespace[64-ACK_STRING_LEN-1];
} TRANS_Packet;

void GotCDC_64B_Packet(char *ptr);
void changeSamplingtime(uint8_t sampletime);
void changeADCclock(uint8_t adcclock);
void changeADCmode(uint8_t adcmode);
//void disableDMAIT(DMA_HandleTypeDef *const hdma);
//void enableDMAIT(DMA_HandleTypeDef *const hdma);

#endif /* SRC_DACPROCESS_H_ */
