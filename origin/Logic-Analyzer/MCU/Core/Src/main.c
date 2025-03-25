/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
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
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"
#include "stm32f3xx.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */
uint16_t buttonState = 0;
//#define BUFFER_SIZE 1024
#define BUFFER_SIZE 4096 // Default size is 1024
uint16_t buffer[BUFFER_SIZE];
uint16_t bufferPointer = 0;
uint8_t Buff[10];
int trigger = 0;
int Period_T;
char msg[10];
char msg2[10];
int samples = 0;
int val = 0;
int status = 1;
uint16_t xorResult = 0;
int trigcounter = 0;
enum triggerStates{triggerState, postTrigger, preTrigger};
enum triggerStates state;
int counter = 0;
uint16_t triggerPeriod = 0x0000;
int trigPointer = 0;
#define MAX_VALUES 2  // Number of values associated with each command
#define MAX_CMD_LENGTH 64  // Maximum command string length
/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */
#define USB_TX_BUFFER_SIZE 64  // Max USB packet size for Full Speed

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim16;

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_TIM2_Init(uint32_t period);
static void MX_TIM16_Init(uint16_t period, uint16_t prescaler);
void change_prescalar16(uint16_t prescalar);
void Process_USB_Command(char *cmd);
void change_period2(uint32_t period);
void change_period16(uint16_t period);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */

typedef enum {
	TenBit = 0x03FF,
	ElevenBit = 0x07FF,
	TwelveBit = 0x0FFF,
	ThirteenBit = 0x1FFF,
	FourteenBit = 0x3FFF,
	FifteenBit = 0x7FFF,
	SixteenBit = 0xFFFF
} NumBits;

uint8_t cout = 0;

void delay_us(uint32_t us) {
    // Enable the DWT cycle counter
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0; // Reset cycle counter
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk; // Enable cycle counter

    // Calculate the number of cycles needed for the delay
    uint32_t cycles = (SystemCoreClock / 1000000L) * us;

    // Wait until the number of cycles has elapsed
    while (DWT->CYCCNT < cycles);
}

int main(void)
{
  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
   HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_TIM2_Init(0x00008CA0);
  MX_USB_DEVICE_Init();
  MX_TIM16_Init(0xFFFF, 1);
  /* USER CODE BEGIN 2 */
  state = preTrigger;
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
 // HAL_TIM_Base_Start_IT(&htim16);//test remove later.
  while (1)
    {
      /* USER CODE END WHILE */
  	  switch(state){
  	  	  	  case preTrigger:
  	  	  		  break;
  	  	  	  case triggerState:

  	  	  		  break;
  	  	  	  case postTrigger:

  	  	  		 if(val == BUFFER_SIZE){
  	  	  			 val = 0;
  	  	  	  	 }

  	  	  		 trigger = 0;
  	  	  		 //Send_Large_USB_Data((void*)buffer, 150 * sizeof(uint16_t));
				 counter++;
				 if(val == bufferPointer - 1){
					 cout++;
				 }
  	  	  		 sprintf(msg, "%hu\r\n", buffer[val]);
  	  	  		 CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
  	  	  		 delay_us(100);
//  	  	  		 HAL_Delay(1);
  	  	  		 val++;
/// creat a counter starting from 0 to 1024 and send the data from bufferpointer to 1024
  	  	  		 if (val == bufferPointer) {
  	  	  			counter = 0;
  	  	  			memset(buffer, 0, sizeof(buffer));
					HAL_TIM_PWM_Start_IT(&htim2, TIM_CHANNEL_1);
					state = preTrigger;
  	  	  		 }
  	  	  			break;

  //	  	  		 if(status == 0){
  //	  	  		 HAL_TIM_PWM_Start_IT(&htim2, TIM_CHANNEL_1);
  //	  	  		  break;

  	      /* USER CODE BEGIN 3 */
  	    }
  	    /* USER CODE END 3 */
  	  }
      /* USER CODE BEGIN 3 */
    }
    /* USER CODE END 3 */

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  RCC_OscInitStruct.PLL.PREDIV = RCC_PREDIV_DIV1;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_USB|RCC_PERIPHCLK_TIM16
                              |RCC_PERIPHCLK_TIM2;
  PeriphClkInit.USBClockSelection = RCC_USBCLKSOURCE_PLL_DIV1_5;
  PeriphClkInit.Tim16ClockSelection = RCC_TIM16CLK_HCLK;
  PeriphClkInit.Tim2ClockSelection = RCC_TIM2CLK_HCLK;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief TIM2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM2_Init(uint32_t period)
{

  /* USER CODE BEGIN TIM2_Init 0 */

  /* USER CODE END TIM2_Init 0 */

  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};

  /* USER CODE BEGIN TIM2_Init 1 */

  /* USER CODE END TIM2_Init 1 */
  htim2.Instance = TIM2;
  htim2.Init.Prescaler = 1;
  htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim2.Init.Period = period-1;
  htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_PWM_Init(&htim2) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim2, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  if (HAL_TIM_PWM_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM2_Init 2 */

  /* USER CODE END TIM2_Init 2 */

}

/**
  * @brief TIM16 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM16_Init(uint16_t period, uint16_t prescalar)
{

  /* USER CODE BEGIN TIM16_Init 0 */

  /* USER CODE END TIM16_Init 0 */

  /* USER CODE BEGIN TIM16_Init 1 */

  /* USER CODE END TIM16_Init 1 */
  htim16.Instance = TIM16;
  htim16.Init.Prescaler =prescalar ;
  htim16.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim16.Init.Period = period;
  htim16.Init.ClockDivision = TIM_CLOCKDIVISION_DIV4;
  htim16.Init.RepetitionCounter = 0;
  htim16.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim16) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM16_Init 2 */
  __HAL_TIM_ENABLE_IT(&htim16, TIM_IT_UPDATE);
  /* USER CODE END TIM16_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
/* USER CODE BEGIN MX_GPIO_Init_1 */
/* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin : B1_Pin */
  GPIO_InitStruct.Pin = B1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(B1_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pin : LD2_Pin */
  GPIO_InitStruct.Pin = LD2_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(LD2_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pins : PB0 PB1 PB2 PB10
                           PB11 PB12 PB13 PB14
                           PB15 PB3 PB4 PB5
                           PB6 PB7 PB8 PB9 */
  GPIO_InitStruct.Pin = GPIO_PIN_0|GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_10
                          |GPIO_PIN_11|GPIO_PIN_12|GPIO_PIN_13|GPIO_PIN_14
                          |GPIO_PIN_15|GPIO_PIN_3|GPIO_PIN_4|GPIO_PIN_5
                          |GPIO_PIN_6|GPIO_PIN_7|GPIO_PIN_8|GPIO_PIN_9;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLDOWN;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

/* USER CODE BEGIN MX_GPIO_Init_2 */
/* USER CODE END MX_GPIO_Init_2 */
}

uint8_t trigPin = 0x00;
uint8_t trigEdge = 0x00; //Falling Edge
int triggerCount = 300;
int Cutter=0;

// ISR for Timer 16
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {

	if(htim == &htim16){
		HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);
		state = postTrigger;
		val = bufferPointer;
		HAL_TIM_PWM_Stop_IT(&htim2, TIM_CHANNEL_1);
		HAL_TIM_Base_Stop_IT(&htim16);
	}

	}

uint8_t IncFlag = 0; // Flag to see if we're on the second value.

// ISR for Timer 2
void HAL_TIM_PWM_PulseFinishedCallback(TIM_HandleTypeDef *htim) {

	// Read the current value from the input pin
	uint16_t currentValue = GPIOB->IDR;

    if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_1) {
        if (!trigger && IncFlag) {
            xorResult = currentValue ^ buffer[bufferPointer];
            uint16_t trigPinCheck = xorResult & trigPin;
            uint16_t trigEdgeCheck = ~(buffer[bufferPointer] ^ trigEdge);
            trigger = (trigPinCheck & trigEdgeCheck) > 0;
            if (trigger) {
            	IncFlag = 0;
                state = triggerState;
                trigPointer = bufferPointer;
                HAL_TIM_Base_Start_IT(&htim16); // Start timer 16
            }
        }
    }

	// Add 8-bit logic input to the buffer if not disconnected
	buffer[bufferPointer] = currentValue;
	// Increment pointer with circular logic
	bufferPointer++;
	bufferPointer &= TwelveBit; // Default: 0x03FF for 10 Bits

	if(bufferPointer == BUFFER_SIZE-1){IncFlag = 1;}

}


uint8_t buff[100] ;
int command = 0;
int temp = 0;
int commandValueFlag = 2; //0 is command, 1 is value 1, 2 is value 2, repeat
uint16_t period16 = 0x0000;
uint32_t period2 = 0x00000000;
uint16_t period2LowerHalf = 0x0000;
uint32_t period2UpperHalf = 0x00000000;
uint16_t prescalar16 = 0x0000;
int puff[100];
int i = 0;
void Process_USB_Command(char *cmd) {




	commandValueFlag += 1;
	if (commandValueFlag == 3)
			commandValueFlag = 0;
	if (commandValueFlag == 0){
		command = atoi(cmd);
		puff[i++] = command;
	}
	else{
			switch(command){
			case 0://start
				HAL_TIM_PWM_Start_IT(&htim2, TIM_CHANNEL_1);
				state = preTrigger;
				break;
			case 1: //stop
				trigger = 0;
				HAL_TIM_PWM_Stop_IT(&htim2, TIM_CHANNEL_1);
				state = preTrigger;
				break;
			case 2: // set trig edge
				trigEdge = atoi(cmd);
				break;
			case 3: // set trig pin
				trigPin = atoi(cmd);
				break;
			case 4: //trigger PIN from 0 to 7
				period16 = period16 << 8;
				period16 |= atoi(cmd);
				change_period16(period16);
				break;

			case 5:
				period2UpperHalf = period2UpperHalf << 8;
				period2UpperHalf |= atoi(cmd);
				period2 &= 0x0000FFFF;
				period2 |= period2UpperHalf << 16;
				change_period2(period2);
				break;
			case 6:
				period2LowerHalf = period2LowerHalf << 8;
				period2LowerHalf |= atoi(cmd);
				period2 &= 0xFFFF0000;
				period2 |= period2LowerHalf;
				change_period2(period2);
				break;
			case 7:
				prescalar16 = prescalar16 << 8;
				prescalar16 |= atoi(cmd);
				change_prescalar16(prescalar16);
				break;
			}
	}
	 memset(cmd, 0, strlen(cmd));  // Clear the command string//clear command

}
void change_period2(uint32_t period){
	HAL_TIM_PWM_Stop(&htim2, TIM_CHANNEL_1);

	memset(buffer, 0, sizeof(buffer));

	MX_TIM2_Init(period);
	HAL_TIM_PWM_Start_IT(&htim2, TIM_CHANNEL_1);

}
void change_period16(uint16_t period){
	HAL_TIM_Base_Stop(&htim16);

	MX_TIM16_Init(period, prescalar16);
}
void change_prescalar16(uint16_t prescalar){
	HAL_TIM_Base_Stop(&htim16);

	MX_TIM16_Init(period16, prescalar);
}
/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
