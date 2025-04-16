/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2024 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h5xx_hal.h"
#include "stm32h5xx_nucleo.h"
#include <stdio.h>

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#define datalength 8
#define PACK __attribute__((packed))
typedef struct PACK {
    uint8_t packet_type;
    uint16_t adcpos;
    uint16_t logicpos;
    //uint8_t oscch1[4];
    //uint8_t oscch2[4];
    //uint8_t logic[4];
    uint16_t oscch1[datalength];
    uint16_t oscch2[datalength];
    uint16_t logic[datalength];
    uint8_t whitespace[11];

    //uint8_t datastring[63];
} DATA_Packet;
/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */
void gotcommand(char *command[]);
void adjustPLL2(uint32_t PLL2Radjust, uint32_t PLL2Nadjust);
void ADCstop();
void ADCstart();
void sendData(int adcoffset, int logicoffset);
void sendADCData(int offset);
void sendLogicData(int offset);

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define TRACE_CK_Pin GPIO_PIN_2
#define TRACE_CK_GPIO_Port GPIOE
#define TRACE_D0_Pin GPIO_PIN_3
#define TRACE_D0_GPIO_Port GPIOE
#define TRACE_D1_Pin GPIO_PIN_4
#define TRACE_D1_GPIO_Port GPIOE
#define TRACE_D2_Pin GPIO_PIN_5
#define TRACE_D2_GPIO_Port GPIOE
#define TRACE_D3_Pin GPIO_PIN_6
#define TRACE_D3_GPIO_Port GPIOE
#define STLK_MCO_Pin GPIO_PIN_0
#define STLK_MCO_GPIO_Port GPIOH
#define RMII_MDC_Pin GPIO_PIN_1
#define RMII_MDC_GPIO_Port GPIOC
#define RMII_REF_CLK_Pin GPIO_PIN_1
#define RMII_REF_CLK_GPIO_Port GPIOA
#define RMII_MDIO_Pin GPIO_PIN_2
#define RMII_MDIO_GPIO_Port GPIOA
#define RMII_RXD0_Pin GPIO_PIN_4
#define RMII_RXD0_GPIO_Port GPIOC
#define RMII_RXD1_Pin GPIO_PIN_5
#define RMII_RXD1_GPIO_Port GPIOC
#define CH2_ATTENUATOR_Pin GPIO_PIN_1
#define CH2_ATTENUATOR_GPIO_Port GPIOG
#define CH2_AC_DC_Pin GPIO_PIN_7
#define CH2_AC_DC_GPIO_Port GPIOE
#define GAIN_C1_Pin GPIO_PIN_12
#define GAIN_C1_GPIO_Port GPIOE
#define GAIN_C0_Pin GPIO_PIN_13
#define GAIN_C0_GPIO_Port GPIOE
#define CH2_1_1_AMP_Pin GPIO_PIN_14
#define CH2_1_1_AMP_GPIO_Port GPIOE
#define CH2_1_2_5_AMP_Pin GPIO_PIN_15
#define CH2_1_2_5_AMP_GPIO_Port GPIOE
#define CH2_1_5_AMP_Pin GPIO_PIN_10
#define CH2_1_5_AMP_GPIO_Port GPIOB
#define UCPD_CC1_Pin GPIO_PIN_13
#define UCPD_CC1_GPIO_Port GPIOB
#define UCPD_CC2_Pin GPIO_PIN_14
#define UCPD_CC2_GPIO_Port GPIOB
#define RMII_TXD1_Pin GPIO_PIN_15
#define RMII_TXD1_GPIO_Port GPIOB
#define UCPD_FLT_Pin GPIO_PIN_7
#define UCPD_FLT_GPIO_Port GPIOG
#define UCDP_DBn_Pin GPIO_PIN_9
#define UCDP_DBn_GPIO_Port GPIOA
#define USB_FS_N_Pin GPIO_PIN_11
#define USB_FS_N_GPIO_Port GPIOA
#define USB_FS_P_Pin GPIO_PIN_12
#define USB_FS_P_GPIO_Port GPIOA
#define SWDIO_Pin GPIO_PIN_13
#define SWDIO_GPIO_Port GPIOA
#define SWCLK_Pin GPIO_PIN_14
#define SWCLK_GPIO_Port GPIOA
#define T_JTDI_Pin GPIO_PIN_15
#define T_JTDI_GPIO_Port GPIOA
#define CH1_1_1_AMP_Pin GPIO_PIN_10
#define CH1_1_1_AMP_GPIO_Port GPIOC
#define CH1_1_2_5_AMP_Pin GPIO_PIN_11
#define CH1_1_2_5_AMP_GPIO_Port GPIOC
#define CH1_1_5_AMP_Pin GPIO_PIN_12
#define CH1_1_5_AMP_GPIO_Port GPIOC
#define CH1_1_10_AMP_Pin GPIO_PIN_0
#define CH1_1_10_AMP_GPIO_Port GPIOD
#define CH1_ATTENUATOR_Pin GPIO_PIN_1
#define CH1_ATTENUATOR_GPIO_Port GPIOD
#define CH1_AC_DC_Pin GPIO_PIN_2
#define CH1_AC_DC_GPIO_Port GPIOD
#define External_LED0_Pin GPIO_PIN_4
#define External_LED0_GPIO_Port GPIOD
#define External_LED1_Pin GPIO_PIN_5
#define External_LED1_GPIO_Port GPIOD
#define External_LED2_Pin GPIO_PIN_6
#define External_LED2_GPIO_Port GPIOD
#define External_LED3_Pin GPIO_PIN_7
#define External_LED3_GPIO_Port GPIOD
#define RMII_TXT_EN_Pin GPIO_PIN_11
#define RMII_TXT_EN_GPIO_Port GPIOG
#define RMI_TXD0_Pin GPIO_PIN_13
#define RMI_TXD0_GPIO_Port GPIOG
#define SWO_Pin GPIO_PIN_3
#define SWO_GPIO_Port GPIOB
#define ARD_D1_TX_Pin GPIO_PIN_6
#define ARD_D1_TX_GPIO_Port GPIOB
#define ARD_D0_RX_Pin GPIO_PIN_7
#define ARD_D0_RX_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */
//extern uint8_t command_buffer[64];

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
