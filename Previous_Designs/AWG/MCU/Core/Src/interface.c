#include "interface.h"
#include "stm32f3xx.h"
#include "usb_device.h"

uint8_t awg_lut[AWG_NUM_CHAN][AWG_SAMPLES*2];

uint16_t BULK_BUFF_RECV = 0;
uint8_t *BULK_BUFF;

extern DAC_HandleTypeDef hdac1;

extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim6;
extern TIM_HandleTypeDef htim7;
extern DMA_HandleTypeDef hdma_dac1_ch1;
extern DMA_HandleTypeDef hdma_dac1_ch2;


const uint8_t ACK_STRING[ACK_STRING_LEN] = {'S', 'T', 'M', 'A', 'W', 'G', '2', '3'};
const uint8_t HS_STRING[HS_STRING_LEN] = {'I', 'N', 'I', 'T'};

void SendAck(){
    TRANS_Packet pack;
    pack.packet_type = 0;
    memcpy(pack.ack_string, ACK_STRING, ACK_STRING_LEN);
    if (CDC_Transmit_FS(&pack, sizeof(TRANS_Packet))) {
        //printLine("BUSY");
    }
}

uint16_t numSamples[AWG_NUM_CHAN];
uint16_t phaseARR[AWG_NUM_CHAN];
uint16_t ARR_hold[AWG_NUM_CHAN];

void GotCDC_64B_Packet(char *ptr) {

    if (!BULK_BUFF_RECV) {
        RECV_Packet *packet = (RECV_Packet *) ptr;
        if (packet->packet_type == 0) {
            // Handle Handshake packet as before
            uint8_t *magic = &(packet->Content.HandShake.handshake_string);

            int match = 1;
            for (int i = 0; i < HS_STRING_LEN; i++) {
                if (magic[i] != HS_STRING[i]) match = 0;
            }
            if (match) {
                SendAck();
            }
        } else if (packet->packet_type == 1) {
            uint8_t chan = packet->Content.AWG_SET.channel;
            uint16_t PSC = packet->Content.AWG_SET.PSC;
            uint16_t ARR = packet->Content.AWG_SET.ARR;
            uint16_t CCR_offset = packet->Content.AWG_SET.CCR_offset;
            numSamples[chan] = packet->Content.AWG_SET.numSamples;
            phaseARR[chan] = packet->Content.AWG_SET.phaseARR;
            uint8_t gain = packet->Content.AWG_SET.gain;




            BULK_BUFF_RECV = numSamples[chan] < 32 ? 128 : numSamples[chan] *2;
            BULK_BUFF = (uint8_t *) awg_lut[chan];

            if(chan == 0){
            	TIM2->CCR1 = CCR_offset;
            	TIM6->ARR = ARR;
            	TIM6->PSC = PSC;
            	ARR_hold[0] = ARR;
            	HAL_GPIO_WritePin(GAIN_C0_GPIO_Port, GAIN_C0_Pin, gain);
            }else{
            	TIM2->CCR2 = CCR_offset;
            	TIM7->ARR = ARR;
            	TIM7->PSC = PSC;

            	ARR_hold[1] = ARR;
            	HAL_GPIO_WritePin(GAIN_C1_GPIO_Port, GAIN_C1_Pin, gain);
            }

            //restart both channels to get correct phase
        	//stop both timers (without using HAL_TIM_Base_Stop to prevent side effects)
        	 __HAL_TIM_DISABLE(&htim6);
        	 __HAL_TIM_DISABLE(&htim7);

        	//restart both DMAs
            HAL_DAC_Stop_DMA(&hdac1, DAC_CHANNEL_1);
         	HAL_DAC_Stop_DMA(&hdac1, DAC_CHANNEL_2);
        	HAL_DAC_Start_DMA(&hdac1, DAC_CHANNEL_1, (uint32_t*)awg_lut[0], numSamples[0], DAC_ALIGN_12B_R);
        	HAL_DAC_Start_DMA(&hdac1, DAC_CHANNEL_2, (uint32_t*)awg_lut[1], numSamples[1], DAC_ALIGN_12B_R);

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
    } else {
        memcpy(BULK_BUFF, ptr, 64);
        BULK_BUFF += 64;
        BULK_BUFF_RECV -= 64;

        if (!BULK_BUFF_RECV) {
            SendAck();
        }
    }
}

