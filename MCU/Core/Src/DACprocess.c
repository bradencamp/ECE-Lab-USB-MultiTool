#include "DACprocess.h"
#include "stm32h5xx.h"
#include <usbd_cdc_if.h>
#include <main.h>
#include <stm32h5xx_ll_dma.h>

uint8_t awg_lut[AWG_NUM_CHAN][AWG_SAMPLES*2];

uint16_t BULK_BUFF_RECV = 0;
uint8_t *BULK_BUFF;
extern uint8_t pauseTransmit;
extern uint8_t ADCmode;
extern enum triggerStates{triggerState, postTrigger, preTrigger, noTrigger};
extern enum triggerStates Logicstate, ADCstate;

extern uint8_t trigEdge, trigPin;
extern uint16_t prescaler16, period16;
extern uint32_t period32;


extern DAC_HandleTypeDef hdac1;
extern ADC_HandleTypeDef hadc1;
extern ADC_HandleTypeDef hadc2;

extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim6;
extern TIM_HandleTypeDef htim7;
extern TIM_HandleTypeDef htim8; //For ADC
extern TIM_HandleTypeDef htim17; //For ADC
extern TIM_HandleTypeDef htim5; //For logic
extern TIM_HandleTypeDef htim16; //For logic

extern DMA_HandleTypeDef handle_GPDMA1_Channel1;
extern DMA_HandleTypeDef handle_GPDMA1_Channel2;
extern DMA_HandleTypeDef handle_GPDMA2_Channel0;
extern DMA_HandleTypeDef handle_GPDMA2_Channel1;
extern DMA_HandleTypeDef hdma_adc1;
extern DMA_HandleTypeDef hdma_adc2;

extern void changeLogic();


const uint8_t ACK_STRING[ACK_STRING_LEN] = {'S', 'T', 'M', 'A', 'W', 'G', '2', '3'};
const uint8_t HS_STRING[HS_STRING_LEN] = {'I', 'N', 'I', 'T'};

void SendAck(){
	//HAL_GPIO_WritePin(GPIOD, GPIO_PIN_5, GPIO_PIN_SET);
    TRANS_Packet pack;
    char whitespace0[64-ACK_STRING_LEN-1];
    pack.packet_type = 0;
    memcpy(pack.ack_string, ACK_STRING, ACK_STRING_LEN);
    memcpy(pack.whitespace, whitespace0, (64-ACK_STRING_LEN-1));
    if (CDC_Transmit_FS(&pack, sizeof(TRANS_Packet))) {
        //printLine("BUSY");
    }


}

uint16_t numSamples[AWG_NUM_CHAN];
uint16_t phaseARR[AWG_NUM_CHAN];
uint16_t ARR_hold[AWG_NUM_CHAN];

void GotCDC_64B_Packet(char *ptr) {
	pauseTransmit=1;
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
            HAL_GPIO_TogglePin(GPIOD, GPIO_PIN_6);

        }
        else if (packet->packet_type == 1) {
        	//HAL_GPIO_WritePin(GPIOD, GPIO_PIN_5, GPIO_PIN_SET);
        	//HAL_GPIO_WritePin(GPIOD, GPIO_PIN_4, GPIO_PIN_RESET);
        	SendAck();
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
            	TIM1->CCR1 = CCR_offset;
            	TIM6->ARR = ARR;
            	TIM6->PSC = PSC;
            	ARR_hold[0] = ARR;
            	HAL_GPIO_WritePin(GPIOE, GPIO_PIN_13, gain);
            }else{
            	TIM1->CCR2 = CCR_offset;
            	TIM7->ARR = ARR;
            	TIM7->PSC = PSC;
            	ARR_hold[1] = ARR;
            	HAL_GPIO_WritePin(GPIOE, GPIO_PIN_12, gain);
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

        	//HAL_DAC_Init(&hdac1);
        	//HAL_DAC_Start_DMA(&hdac1, DAC_CHANNEL_2, (uint32_t *)baEscalator8bit, 6, DAC_ALIGN_12B_R);
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
        else if(packet->packet_type == 2){ //ADC packet. First configure GPIO outputs, then adjust the ADC sampling rate, lastly change things depending on trigger mode
        	//HAL_GPIO_WritePin(GPIOD, GPIO_PIN_4, GPIO_PIN_SET);
        	//HAL_GPIO_WritePin(GPIOD, GPIO_PIN_5, GPIO_PIN_SET);
        	SendAck();
            uint8_t chan = packet->Content.ADC_SET.channel;
            uint8_t adcmode = packet->Content.ADC_SET.adcmode;
            uint8_t triggermode = packet->Content.ADC_SET.triggermode;
            uint16_t triggerval = packet->Content.ADC_SET.triggerval;
            uint8_t sample = packet->Content.ADC_SET.sampletime;
            uint8_t offset = packet->Content.ADC_SET.offset;
            uint8_t attenuation = packet->Content.ADC_SET.attenuation;
			uint8_t amp10 = packet->Content.ADC_SET.amp10;
			uint8_t amp5 = packet->Content.ADC_SET.amp5;
			uint8_t amp2_5 = packet->Content.ADC_SET.amp2_5;
			uint8_t amp1 = packet->Content.ADC_SET.amp1;

			 if(chan == 0){	//Configure GPIO outputs
				//HAL_GPIO_WritePin(GPIOD, GPIO_PIN_5, GPIO_PIN_RESET);
				HAL_GPIO_WritePin(GPIOD, GPIO_PIN_2, offset); //Pin PD2 AC/DC offset
				HAL_GPIO_WritePin(GPIOD, GPIO_PIN_1, attenuation); //Pin PD1 Attenuation
				HAL_GPIO_WritePin(GPIOD, GPIO_PIN_0, amp10); //Pin PD0 1:10 amp
				HAL_GPIO_WritePin(GPIOC, GPIO_PIN_12, amp5); //Pin PC12 1:5 amp
				HAL_GPIO_WritePin(GPIOC, GPIO_PIN_11, amp2_5); //Pin PC11 1:2.5 amp
				HAL_GPIO_WritePin(GPIOC, GPIO_PIN_10, amp1); //Pin PC10 1:1 amp
				//HAL_ADC_Stop_DMA(&hadc1);
				//changeSampling(&hadc1, sample);
				//HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);

			 }
			 if(chan == 1){
				//HAL_GPIO_WritePin(GPIOD, GPIO_PIN_5, GPIO_PIN_SET);
				HAL_GPIO_WritePin(GPIOE, GPIO_PIN_7, offset); //Pin PE7 AC/DC offset
				HAL_GPIO_WritePin(GPIOG, GPIO_PIN_1, attenuation); //Pin PG1 Attenuation
				HAL_GPIO_WritePin(GPIOG, GPIO_PIN_0, amp10); //Pin PG0 1:10 amp
				HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, amp5); //Pin PF12 1:5 amp
				HAL_GPIO_WritePin(GPIOE, GPIO_PIN_15, amp2_5); //Pin PF11 1:2.5 amp
				HAL_GPIO_WritePin(GPIOE, GPIO_PIN_14, amp1); //Pin PF10 1:1 amp
				//HAL_ADC_Stop_DMA(&hadc2);
				//changeSampling(&hadc2, sample);
				//HAL_ADC_Start_DMA(&hadc2, (uint32_t*)adc_buff, ADC_BUFF);
			 }
			 ADCstop();
			 changeADCmode(adcmode);
			 switch(triggermode){
			 	 case 0: ADCstate=noTrigger; //No trigger (sample and send). Enable interrupts pertaining to transfer complete and disable those related to the AWD
					 ADC1->CR &=~ADC_CR_ADSTART; ADC2->CR &=~ADC_CR_ADSTART;
					 //ADC1->IER &=~ADC_IER_AWD1IE; ADC2->IER &=~ADC_IER_AWD1IE;
					 //ADC1->IER &=~ADC_IER_AWD2IE; ADC2->IER &=~ADC_IER_AWD2IE;
					 disableAWDIT(&hadc1);
					 disableAWDIT(&hadc2);
					 enableDMAIT(&handle_GPDMA2_Channel0);
					 enableDMAIT(&handle_GPDMA2_Channel1); //Not needed but whatev
			 	 	 	 break;
			 	 case 1: ADCstate=preTrigger; //Rising edge trigger. Start ADC, disable HT and  TC, enable AWD1 and AWD2
					 ADC1->CR |=ADC_CR_ADSTART; ADC2->CR |=ADC_CR_ADSTART;
					 disableDMAIT(&handle_GPDMA2_Channel0);
					 disableDMAIT(&handle_GPDMA2_Channel1);
						//ADC1_ADC_CR->JADSTART=0;  LL_ADC_ConfigAnalogWDThresholds
						//ADC1->ADC_CR->ADSTART=0; AWDCH2
			 	 	 	 //ADC1->ADC_TR1->LT1=(triggerval-5);
			 	 	 	 //ADC1->ADC_TR1->HT1=(triggerval+5);break;
					 if(chan==0){ //Rising edge so set AWD2 to trigger lower than AWD1
						 //LL_ADC_SetAnalogWDThresholds(ADC1, 0x01U, (triggerval-5), (triggerval+5));
						 //LL_ADC_SetAnalogWDThresholds(ADC1, 0x02U, (triggerval-55), (triggerval-45));
						 //ADC2->AWD2CR |= ADC_AWD2CR_AWD2CH;
						 LL_ADC_SetAnalogWDMonitChannels(ADC1, LL_ADC_AWD1, LL_ADC_AWD_CHANNEL_0_REG);
						 LL_ADC_SetAnalogWDMonitChannels(ADC1, LL_ADC_AWD2, LL_ADC_AWD_CHANNEL_0_REG);

						 LL_ADC_SetAnalogWDThresholds(ADC1, LL_ADC_AWD1, LL_ADC_AWD_THRESHOLD_HIGH, (triggerval+15));
						 LL_ADC_SetAnalogWDThresholds(ADC1, LL_ADC_AWD1, LL_ADC_AWD_THRESHOLD_LOW, (triggerval-15));
						 LL_ADC_SetAnalogWDThresholds(ADC1, LL_ADC_AWD2, LL_ADC_AWD_THRESHOLD_HIGH, (triggerval-35)>>4);
						 LL_ADC_SetAnalogWDThresholds(ADC1, LL_ADC_AWD2, LL_ADC_AWD_THRESHOLD_LOW, (triggerval-65)>>4);
						 enableAWDIT(&hadc1);
					 }
					 else{
						 LL_ADC_SetAnalogWDMonitChannels(ADC2, LL_ADC_AWD1, LL_ADC_AWD_CHANNEL_3_REG);
						 LL_ADC_SetAnalogWDMonitChannels(ADC2, LL_ADC_AWD2, LL_ADC_AWD_CHANNEL_3_REG);

						 LL_ADC_SetAnalogWDThresholds(ADC2, LL_ADC_AWD1, LL_ADC_AWD_THRESHOLD_HIGH, (triggerval+15));
						 LL_ADC_SetAnalogWDThresholds(ADC2, LL_ADC_AWD1, LL_ADC_AWD_THRESHOLD_LOW, (triggerval-15));
						 LL_ADC_SetAnalogWDThresholds(ADC2, LL_ADC_AWD2, LL_ADC_AWD_THRESHOLD_HIGH, (triggerval-35)>>4);
						 LL_ADC_SetAnalogWDThresholds(ADC2, LL_ADC_AWD2, LL_ADC_AWD_THRESHOLD_LOW, (triggerval-65)>>4);
						 enableAWDIT(&hadc2);
					 }
					 break;
			 	 case 2: ADCstate=preTrigger; //Falling edge trigger, same logic as rising edge trigger

		 	 	 	 disableDMAIT(&handle_GPDMA2_Channel0);
		 	 	 	 disableDMAIT(&handle_GPDMA2_Channel1);
					 if(chan==0){
						 LL_ADC_SetAnalogWDMonitChannels(ADC1, LL_ADC_AWD1, LL_ADC_AWD_CHANNEL_0_REG);
						 LL_ADC_SetAnalogWDMonitChannels(ADC1, LL_ADC_AWD2, LL_ADC_AWD_CHANNEL_0_REG);

						 LL_ADC_SetAnalogWDThresholds(ADC1, LL_ADC_AWD1, LL_ADC_AWD_THRESHOLD_HIGH, (triggerval+15));
						 LL_ADC_SetAnalogWDThresholds(ADC1, LL_ADC_AWD1, LL_ADC_AWD_THRESHOLD_LOW, (triggerval-15));
						 LL_ADC_SetAnalogWDThresholds(ADC1, LL_ADC_AWD2, LL_ADC_AWD_THRESHOLD_HIGH, (triggerval+65)>>4);
						 LL_ADC_SetAnalogWDThresholds(ADC1, LL_ADC_AWD2, LL_ADC_AWD_THRESHOLD_LOW, (triggerval+35)>>4);
						 enableAWDIT(&hadc1);
					 }
					 else{
						 LL_ADC_SetAnalogWDMonitChannels(ADC2, LL_ADC_AWD1, LL_ADC_AWD_CHANNEL_3_REG);
						 LL_ADC_SetAnalogWDMonitChannels(ADC2, LL_ADC_AWD2, LL_ADC_AWD_CHANNEL_3_REG);
						 LL_ADC_SetAnalogWDThresholds(ADC2, LL_ADC_AWD1, LL_ADC_AWD_THRESHOLD_HIGH, (triggerval+15));
						 LL_ADC_SetAnalogWDThresholds(ADC2, LL_ADC_AWD1, LL_ADC_AWD_THRESHOLD_LOW, (triggerval-15));
						 LL_ADC_SetAnalogWDThresholds(ADC2, LL_ADC_AWD2, LL_ADC_AWD_THRESHOLD_HIGH, (triggerval+65)>>4);
						 LL_ADC_SetAnalogWDThresholds(ADC2, LL_ADC_AWD2, LL_ADC_AWD_THRESHOLD_LOW, (triggerval+35)>>4);
						enableAWDIT(&hadc2);
					 }
					 break;
			 	 default: ADCstate=noTrigger; break; //break and cry
			 }
			 ADCstart();
			 ADC1->CR |=ADC_CR_ADEN; ADC2->CR |=ADC_CR_ADEN;
			 ADC1->CR |=ADC_CR_ADSTART; ADC2->CR |=ADC_CR_ADSTART;
        }
        else if(packet->packet_type == 3){
        	SendAck();
            uint8_t control = packet->Content.LOGIC_SET.control;
            trigPin = packet->Content.LOGIC_SET.triggerpin;
            trigEdge = packet->Content.LOGIC_SET.triggeredge;
            period16 = packet->Content.LOGIC_SET.period16;
            prescaler16 = packet->Content.LOGIC_SET.prescaler;
            period32 = packet->Content.LOGIC_SET.period32;

            if(control==1){ //Start PWM timer and set to pretrigger
            	HAL_TIM_PWM_Start_IT(&htim5, TIM_CHANNEL_1);
                HAL_TIM_PWM_Stop(&htim5, TIM_CHANNEL_1);
                HAL_TIM_Base_Stop(&htim16);
                changeLogic();
            	HAL_TIM_PWM_Start_IT(&htim5, TIM_CHANNEL_1);
            	Logicstate=preTrigger;
            }
            else{ //Stop
            	HAL_TIM_PWM_Stop_IT(&htim5, TIM_CHANNEL_1);
            	HAL_TIM_Base_Stop(&htim16);
            	Logicstate=preTrigger;
            }

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
    pauseTransmit=0;
}
void changeADCmode(uint8_t mode){

	switch(mode){
		case 0: //5Mhz sampling with shadow sampling at 1/100 or 50Khz
			TIM8->PSC = 25-1; TIM8->ARR = 2-1;
			TIM17->PSC = 500-1; TIM17->ARR = 10-1;
			changeSamplingtime(0); break;
		case 1: //2Mhz sampling
			TIM8->ARR = 5-1;
			TIM17->ARR = 25-1;
			changeSamplingtime(0); break;
		case 2: //1Mhz sampling
			TIM8->ARR = 10-1;
			TIM17->ARR = 50-1;
			changeSamplingtime(2); break;
		case 3: //500Khz sampling
			TIM8->ARR = 20-1;
			TIM17->ARR = 100-1;
			changeSamplingtime(4); break;
		case 4: //200Khz sampling
			TIM8->ARR = 50-1;
			TIM17->ARR = 250-1;
			changeSamplingtime(5); break;
		case 5: //100Khz sampling
			TIM8->ARR = 100-1;
			TIM17->ARR = 500-1;
			changeSamplingtime(6); break;
		case 6: //50Khz sampling
			TIM8->ARR = 200-1;
			TIM17->ARR = 1000-1;
			changeSamplingtime(7); break;
		case 7: //20Khz sampling
			TIM8->ARR = 500-1;
			TIM17->ARR = 2500-1;
			changeSamplingtime(7); break;
		case 8: //10Khz sampling
			TIM8->ARR = 1000-1;
			TIM17->ARR = 5000-1;
			changeSamplingtime(7); break;
		case 9: //5Khz sampling
			TIM8->ARR = 2000-1;
			TIM17->ARR = 10000-1;
			changeSamplingtime(7); break;
		case 10: //2Khz sampling
			TIM8->ARR = 5000-1;
			TIM17->ARR = 25000-1;
			changeSamplingtime(7); break;
		case 11: //1Khz sampling
			TIM8->ARR = 10000-1;
			TIM17->ARR = 50000-1;
			changeSamplingtime(7); break;
		default:
			TIM8->PSC = 25-1; TIM8->ARR = 2-1;
			TIM17->PSC = 500-1; TIM17->ARR = 10-1;
			changeSamplingtime(0); break;
	}

	//Do I even need to stop and restart everything? Maybe not!
	//__HAL_TIM_DISABLE(&htim8);
	//__HAL_TIM_DISABLE(&htim17);
	//ADCstop();
	//ADCstart();

}
void changeSamplingtime(uint8_t sampletime){ //Change the varying sample times for the ADC
	//ADCstop();
	switch (sampletime){
		case 0: LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_0,LL_ADC_SAMPLINGTIME_2CYCLES_5);
				LL_ADC_SetChannelSamplingTime(ADC2, LL_ADC_CHANNEL_3,LL_ADC_SAMPLINGTIME_2CYCLES_5);
				break;
		case 1: LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_0,LL_ADC_SAMPLINGTIME_6CYCLES_5);
				LL_ADC_SetChannelSamplingTime(ADC2, LL_ADC_CHANNEL_3,LL_ADC_SAMPLINGTIME_6CYCLES_5);
				break;
		case 2: LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_0,LL_ADC_SAMPLINGTIME_12CYCLES_5);
				LL_ADC_SetChannelSamplingTime(ADC2, LL_ADC_CHANNEL_3,LL_ADC_SAMPLINGTIME_12CYCLES_5);
				break;
		case 3: LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_0,LL_ADC_SAMPLINGTIME_24CYCLES_5);
				LL_ADC_SetChannelSamplingTime(ADC2, LL_ADC_CHANNEL_3,LL_ADC_SAMPLINGTIME_24CYCLES_5);
				break;
		case 4: LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_0,LL_ADC_SAMPLINGTIME_47CYCLES_5);
				LL_ADC_SetChannelSamplingTime(ADC2, LL_ADC_CHANNEL_3,LL_ADC_SAMPLINGTIME_47CYCLES_5);
				break;
		case 5: LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_0,LL_ADC_SAMPLINGTIME_92CYCLES_5);
				LL_ADC_SetChannelSamplingTime(ADC2, LL_ADC_CHANNEL_3,LL_ADC_SAMPLINGTIME_92CYCLES_5);
				break;
		case 6: LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_0,LL_ADC_SAMPLINGTIME_247CYCLES_5);
				LL_ADC_SetChannelSamplingTime(ADC2, LL_ADC_CHANNEL_3,LL_ADC_SAMPLINGTIME_247CYCLES_5);
				break;
		case 7: LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_0,LL_ADC_SAMPLINGTIME_640CYCLES_5);
				LL_ADC_SetChannelSamplingTime(ADC2, LL_ADC_CHANNEL_3,LL_ADC_SAMPLINGTIME_640CYCLES_5);
				break;
		default:
			break;
	}
	//ADCstart();


}

void disableDMAIT(DMA_HandleTypeDef *const hdma){ //Disables ADC DMA TC and HT interrupts (for triggers)
	const DMA_TypeDef *p_dma_instance = GET_DMA_INSTANCE(hdma);
	LL_DMA_DisableIT_TC(p_dma_instance, 0x00U);
	LL_DMA_DisableIT_TC(p_dma_instance, 0x01U);
	LL_DMA_DisableIT_HT(p_dma_instance, 0x00U);
	LL_DMA_DisableIT_HT(p_dma_instance, 0x01U);

}
void enableDMAIT(DMA_HandleTypeDef *const hdma){ //Disables ADC DMA TC and HT interrupts (for triggers)
	const DMA_TypeDef *p_dma_instance = GET_DMA_INSTANCE(hdma);
	LL_DMA_EnableIT_TC(p_dma_instance, 0x00U);
	LL_DMA_EnableIT_TC(p_dma_instance, 0x01U);
	LL_DMA_EnableIT_HT(p_dma_instance, 0x00U);
	LL_DMA_EnableIT_HT(p_dma_instance, 0x01U);

}
void enableAWDIT(ADC_HandleTypeDef *hadc){ //Enable AWD interrupts
	LL_ADC_EnableIT_AWD1(hadc->Instance);
	LL_ADC_EnableIT_AWD2(hadc->Instance);
	hadc->Instance->ISR |=ADC_ISR_AWD1; //Clear any flags
	hadc->Instance->ISR |=ADC_ISR_AWD2;
}
void disableAWDIT(ADC_HandleTypeDef *hadc){ //Disable AWD interrupts
	LL_ADC_DisableIT_AWD1(hadc->Instance);
	LL_ADC_DisableIT_AWD2(hadc->Instance);
	//hadc->Instance->CFGR &=~ADC_CFGR_AWD1EN; //Clear flag
	//hadc->Instance->CFGR &=~ADC_CFGR_AWD2EN; //Clear flag
	hadc->Instance->ISR |=ADC_ISR_AWD1; //Clear any flags
	hadc->Instance->ISR |=ADC_ISR_AWD2;
}
