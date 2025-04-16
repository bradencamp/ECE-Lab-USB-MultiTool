/*
 * ADCprocess.h
 *
 *  Created on: Jan 20, 2025
 *      Author: Timothy
 */

#ifndef SRC_ADCPROCESS_H_
#define SRC_ADCPROCESS_H_

#include <stdint.h>

#define MAGIC_NUM 0x42
#define HS_STRING_LEN 4
#define ACK_STRING_LEN 8

#define PACK __attribute__((packed))


typedef struct {
    uint8_t packet_type;
    union {
        struct { // packet_type = 2
            uint8_t handshake_string[HS_STRING_LEN];
        } PACK HandShake;
        struct { // packet_type = 3
            uint8_t channel;
            uint8_t adcclock;
            uint8_t sampletime;
            uint8_t offset;
            uint8_t attenuation;
            uint8_t amp10;
            uint8_t amp5;
            uint8_t amp2_5;
            uint8_t amp1;
        } PACK ADC_SET;
    } PACK Content;
} PACK ARECV_Packet;

typedef struct PACK {
    uint8_t packet_type;
    uint8_t ack_string[ACK_STRING_LEN];
} ATRANS_Packet;

//void ADCGotCDC_64B_Packet(char *ptr);
//void changeSampling(ADC_HandleTypeDef* hadc, uint8_t sampletime);
void changeADC1Clock();
#endif /* SRC_ADCPROCESS_H_ */
