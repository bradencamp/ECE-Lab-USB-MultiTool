/*
 * ADCprocess.c
 *
 *  Created on: Jan 20, 2025
 *      Author: Timothy
 */
#include "ADCprocess.h"
#include "stm32h5xx.h"
#include <usbd_cdc_if.h>

//uint16_t BULK_BUFF_RECV = 0;
//uint8_t *BULK_BUFF;
/*
void ADCGotCDC_64B_Packet(char *ptr) {
    if (!BULK_BUFF_RECV) {
        RECV_Packet *packet = (RECV_Packet *) ptr;
        if (packet->packet_type == 2) {

            // Handle Handshake packet as before
            uint8_t *magic = &(packet->Content.HandShake.handshake_string);

            int match = 1;
            for (int i = 0; i < HS_STRING_LEN; i++) {
                if (magic[i] != HS_STRING[i]) match = 0;
            }
            if (match) {
                SendAck();
            }
        } else if (packet->packet_type == 3) {
        	HAL_GPIO_WritePin(GPIOD, GPIO_PIN_5, GPIO_PIN_SET);
            uint8_t chan = packet->Content.ADC_SET.channel;
            uint8_t clock = packet->Content.ADC_SET.adcclock;
            uint8_t sample = packet->Content.ADC_SET.sampletime;
            uint8_t offset = packet->Content.ADC_SET.offset;
            uint8_t attenuation = packet->Content.ADC_SET.attenuation;
			uint8_t amp10 = packet->Content.ADC_SET.amp10;
			uint8_t amp5 = packet->Content.ADC_SET.amp5;
			uint8_t amp2_5 = packet->Content.ADC_SET.amp2_5;
			uint8_t amp1 = packet->Content.ADC_SET.amp1;

			//Dont think bulk buff is necessary
            //BULK_BUFF_RECV = numSamples[chan] < 32 ? 128 : numSamples[chan] *2;
            //BULK_BUFF_RECV = 64;
            //BULK_BUFF = (uint8_t *) awg_lut[chan];

            if(chan == 0){	//Configure GPIO outputs
            	HAL_GPIO_WritePin(GPIOD, GPIO_PIN_2, offset); //Pin PD2 AC/DC offset
            	HAL_GPIO_WritePin(GPIOD, GPIO_PIN_1, attenuation); //Pin PD1 Attenuation
            	HAL_GPIO_WritePin(GPIOD, GPIO_PIN_0, amp10); //Pin PD0 1:10 amp
            	HAL_GPIO_WritePin(GPIOC, GPIO_PIN_12, amp5); //Pin PC12 1:5 amp
            	HAL_GPIO_WritePin(GPIOC, GPIO_PIN_11, amp2_5); //Pin PC11 1:2.5 amp
            	HAL_GPIO_WritePin(GPIOC, GPIO_PIN_10, amp1); //Pin PC10 1:1 amp
            	HAL_ADC_Stop_DMA(&hadc1);
            	changeSampling(&hadc1, sample);
            	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);

            }else{
            	HAL_GPIO_WritePin(GPIOE, GPIO_PIN_7, offset); //Pin PE7 AC/DC offset
            	HAL_GPIO_WritePin(GPIOG, GPIO_PIN_1, attenuation); //Pin PG1 Attenuation
            	HAL_GPIO_WritePin(GPIOG, GPIO_PIN_0, amp10); //Pin PG0 1:10 amp
            	HAL_GPIO_WritePin(GPIOF, GPIO_PIN_15, amp5); //Pin PF12 1:5 amp
            	HAL_GPIO_WritePin(GPIOF, GPIO_PIN_14, amp2_5); //Pin PF11 1:2.5 amp
            	HAL_GPIO_WritePin(GPIOF, GPIO_PIN_13, amp1); //Pin PF10 1:1 amp
            	HAL_ADC_Stop_DMA(&hadc2);
            	changeSampling(&hadc2, sample);
            	HAL_ADC_Start_DMA(&hadc2, (uint32_t*)adc_buff, ADC_BUFF);
            }

            //restart both channels to get correct phase
        	//stop both timers (without using HAL_TIM_Base_Stop to prevent side effects)
            //unsure if needed for oscilloscope, if so, use timer 16 and 17
        	// __HAL_TIM_DISABLE(&htim6);
        	// __HAL_TIM_DISABLE(&htim7);



        	//reset counters, otherwise prescale counter value can mess up wphase
        	TIM6 -> EGR = TIM_EGR_UG;
        	TIM7 -> EGR = TIM_EGR_UG;

        	//set clock phase
           TIM6->CNT = phaseARR[0] - ARR_hold[1];
            TIM7->CNT = phaseARR[1] - ARR_hold[0];
        	//TIM6->CNT = 0;
        	//TIM7->CNT = 6;

            //restart both timers (again without HAL_TIM_Base_Start).
            //The generated asm code should enable both within two instruction
            //this code is a bit loony and isn't perfectly synchronized anyway
            volatile uint32_t *CCR6_add = &(htim6.Instance->CR1);
           	uint32_t CCR6_new = *CCR6_add | TIM_CR1_CEN;
           	volatile uint32_t *CCR7_add = &(htim7.Instance->CR1);
           	uint32_t CCR7_new = *CCR7_add | TIM_CR1_CEN;
           	*CCR6_add = CCR6_new;
 			*CCR7_add = CCR7_new;
 			//restart of both channels complete
        }
        else{
            if (CDC_Transmit_FS("nopacket", sizeof("nopacket"))) {
                //printLine("BUSY");
            }
        }
    } else {
        memcpy(BULK_BUFF, ptr, 64);
        BULK_BUFF += 64;
        BULK_BUFF_RECV -= 64;

        if (!BULK_BUFF_RECV) {
            SendAck();
        }
    }
}

void changeSampling(ADC_HandleTypeDef* hadc, uint8_t sampletime){
	switch(sampletime){
	case 0:
		LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_1CYCLE_5);
		break;
	case 1:
		break;
	case 2:
		break;
	case 3:
		break;
	case 4:
		break;
	case 5:
		break;
	case 6:
		break;
	case 7:
		break;
	default:
		break;
	}
}
void changeADC1Clock(){

}
*/
