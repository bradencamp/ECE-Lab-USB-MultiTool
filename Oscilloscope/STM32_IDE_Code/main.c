/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2022 STMicroelectronics.
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

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "usbd_cdc_if.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stm32f3xx_ll_adc.h>
#include <stm32f3xx_ll_rcc.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define ADC_BUFF 10000	// can be 20480 make larger buffer => store more data
void changeSampling(ADC_HandleTypeDef* hadc);	// declare function before using it
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
DMA_HandleTypeDef hdma_adc1;

TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim16;
DMA_HandleTypeDef hdma_tim1_ch1;

UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */
uint8_t command_buffer[64];
uint16_t adc_buff[ADC_BUFF];
char offset[5];
char digit1;
char digit2;
char digit3;
char digit4;
int ccr_digit1234=0;
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_ADC1_Init(void);
static void MX_TIM16_Init(void);
static void MX_TIM1_Init(void);
static void MX_USART2_UART_Init(void);
/* USER CODE BEGIN PFP */
void changeADC1Clock1();
void changeADC1Clock2();
void changeADC1Clock4();
void changeADC1Clock6();
void changeADC1Clock8();
void changeADC1Clock10();
void changeADC1Clock12();
void changeADC1Clock16();
void changeADC1Clock32();
void changeADC1Clock64();
void changeADC1Clock128();
void changeADC1Clock256();

void changeSampling0(ADC_HandleTypeDef* hadc);	// declare function before using it
void changeSampling1(ADC_HandleTypeDef* hadc);
void changeSampling2(ADC_HandleTypeDef* hadc);
void changeSampling3(ADC_HandleTypeDef* hadc);
void changeSampling4(ADC_HandleTypeDef* hadc);
void changeSampling5(ADC_HandleTypeDef* hadc);
void changeSampling6(ADC_HandleTypeDef* hadc);
void changeSampling7(ADC_HandleTypeDef* hadc);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
  /* USER CODE BEGIN 1 */
	char msg[10];
	int n=0;
	int a=0;
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
  MX_DMA_Init();
  MX_ADC1_Init();
  MX_TIM16_Init();
  MX_USB_DEVICE_Init();
  MX_TIM1_Init();
  MX_USART2_UART_Init();
  /* USER CODE BEGIN 2 */
  HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
  TIM1->CCR1 = 3300;
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
    {

	  //-------------------Original------------------------------------
	  //TIM1->CCR1 = ccr_digit1234;
	  if (n==10000){
  		  n=0;
  	  }
  	  // copy adc (16 bits) value from buffer to (char) msg
  	  // this sprintf() COPY adc_buff valaue,
  	  // CONVERT to "short unsigned" by %hu, PASTE to msg
  	  sprintf(msg, "%hu\r\n", adc_buff[n]);
  	  CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
  	  HAL_Delay(1);
  	  n++;
  	  if (command_buffer[0]=='1'){				// command string is new?
		  digit1 = command_buffer[4];
		  digit2 = command_buffer[5];
		  digit3 = command_buffer[6];
		  digit4 = command_buffer[7];
		  sprintf(offset, "%c%c%c%c",digit1, digit2, digit3, digit4);
		  sscanf(offset, "%04d", &ccr_digit1234);
		  //--------------------Set ADC Clock-----------------------
		  if (command_buffer[3]=='0' && command_buffer[2]=='0'){
			  changeADC1Clock1();
		  }
		  else if(command_buffer[3]=='1' && command_buffer[2]=='0'){
			  changeADC1Clock2();
		  }
		  else if(command_buffer[3]=='2' && command_buffer[2]=='0'){
			  changeADC1Clock4();
		  }
		  else if(command_buffer[3]=='3' && command_buffer[2]=='0'){
			  changeADC1Clock6();
		  }
		  else if(command_buffer[3]=='4' && command_buffer[2]=='0'){
			  changeADC1Clock8();
		  }
		  else if(command_buffer[3]=='5' && command_buffer[2]=='0'){
			  changeADC1Clock10();
		  }
		  else if(command_buffer[3]=='6' && command_buffer[2]=='0'){
			  changeADC1Clock12();
		  }
		  else if(command_buffer[3]=='7' && command_buffer[2]=='0'){
			  changeADC1Clock16();
		  }
		  else if(command_buffer[3]=='8' && command_buffer[2]=='0'){
			  changeADC1Clock32();
		  }
		  else if(command_buffer[3]=='9' && command_buffer[2]=='0'){
			  changeADC1Clock64();
		  }
		  else if(command_buffer[2]=='1' && command_buffer[3]=='0'){
			  changeADC1Clock128();
		  }
		  else if(command_buffer[2]=='1' && command_buffer[3]=='1'){
			  changeADC1Clock256();
		  }

		  //--------------------Set Sample Time-----------------------
		  if (command_buffer[1]=='0'){			// SMP 1.5 clock cycles
			  changeSampling0(&hadc1);
		  }
		  else if (command_buffer[1]=='1'){	// SMP 2.5 clock cycles
			  changeSampling1(&hadc1);
		  }
		  else if (command_buffer[1]=='2'){	// SMP 4.5 clock cycles
			  changeSampling2(&hadc1);
		  }
		  else if (command_buffer[1]=='3'){	// SMP 7.5 clock cycles
			  changeSampling3(&hadc1);
		  }
		  else if (command_buffer[1]=='4'){	// SMP 19.5 clock cycles
			  changeSampling4(&hadc1);
		  }
		  else if (command_buffer[1]=='5'){	// SMP 61.5 clock cycles
			  changeSampling5(&hadc1);
		  }
		  else if (command_buffer[1]=='6'){	// SMP 181.5 clock cycles
			  changeSampling6(&hadc1);
		  }
		  else if (command_buffer[1]=='7'){	// SMP 601.5 clock cycles
			  changeSampling7(&hadc1);
		  }
		  if (command_buffer[8]=='1'){
			  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_10, SET);
		  }
		  else{
			  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_10, RESET);
		  }
		  if (command_buffer[9]=='1'){
			  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, SET);
		  }
		  else{
			  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, RESET);
		  }
		  if (command_buffer[10]=='1'){
			  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8, SET);
		  }
		  else{
			  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8, RESET);
		  }
		  if (command_buffer[11]=='1'){
			  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_7, SET);
		  }
		  else{
			  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_7, RESET);
		  }
		  if (command_buffer[12]=='1'){
			  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, SET);
		  }
		  else{
			  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, RESET);
		  }
		  if (command_buffer[13]=='1'){
			  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, SET);
		  }
		  else{
			  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, RESET);
		  }
		  command_buffer[0]='0';		// set this command string becomes old
	  }
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    }
  /* USER CODE END 3 */
}

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
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_USB|RCC_PERIPHCLK_USART2
                              |RCC_PERIPHCLK_TIM1|RCC_PERIPHCLK_TIM16
                              |RCC_PERIPHCLK_ADC12;
  PeriphClkInit.Usart2ClockSelection = RCC_USART2CLKSOURCE_PCLK1;
  PeriphClkInit.Adc12ClockSelection = RCC_ADC12PLLCLK_DIV1;
  PeriphClkInit.USBClockSelection = RCC_USBCLKSOURCE_PLL_DIV1_5;
  PeriphClkInit.Tim1ClockSelection = RCC_TIM1CLK_HCLK;
  PeriphClkInit.Tim16ClockSelection = RCC_TIM16CLK_HCLK;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief ADC1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_ADC1_Init(void)
{

  /* USER CODE BEGIN ADC1_Init 0 */

  /* USER CODE END ADC1_Init 0 */

  ADC_MultiModeTypeDef multimode = {0};
  ADC_ChannelConfTypeDef sConfig = {0};

  /* USER CODE BEGIN ADC1_Init 1 */

  /* USER CODE END ADC1_Init 1 */

  /** Common config
  */
  hadc1.Instance = ADC1;
  hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV1;
  hadc1.Init.Resolution = ADC_RESOLUTION_12B;
  hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
  hadc1.Init.ContinuousConvMode = ENABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
  hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 1;
  hadc1.Init.DMAContinuousRequests = ENABLE;
  hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  hadc1.Init.LowPowerAutoWait = DISABLE;
  hadc1.Init.Overrun = ADC_OVR_DATA_OVERWRITTEN;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure the ADC multi-mode
  */
  multimode.Mode = ADC_MODE_INDEPENDENT;
  if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure Regular Channel
  */
  sConfig.Channel = ADC_CHANNEL_1;
  sConfig.Rank = ADC_REGULAR_RANK_1;
  sConfig.SingleDiff = ADC_SINGLE_ENDED;
  sConfig.SamplingTime = ADC_SAMPLETIME_1CYCLE_5;
  sConfig.OffsetNumber = ADC_OFFSET_NONE;
  sConfig.Offset = 0;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN ADC1_Init 2 */

  /* USER CODE END ADC1_Init 2 */

}

/**
  * @brief TIM1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM1_Init(void)
{

  /* USER CODE BEGIN TIM1_Init 0 */

  /* USER CODE END TIM1_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};
  TIM_BreakDeadTimeConfigTypeDef sBreakDeadTimeConfig = {0};

  /* USER CODE BEGIN TIM1_Init 1 */

  /* USER CODE END TIM1_Init 1 */
  htim1.Instance = TIM1;
  htim1.Init.Prescaler = 0;
  htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim1.Init.Period = 3300-1;
  htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 0;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim1, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_TIM_PWM_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterOutputTrigger2 = TIM_TRGO2_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  sConfigOC.OCIdleState = TIM_OCIDLESTATE_RESET;
  sConfigOC.OCNIdleState = TIM_OCNIDLESTATE_RESET;
  if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  sBreakDeadTimeConfig.OffStateRunMode = TIM_OSSR_DISABLE;
  sBreakDeadTimeConfig.OffStateIDLEMode = TIM_OSSI_DISABLE;
  sBreakDeadTimeConfig.LockLevel = TIM_LOCKLEVEL_OFF;
  sBreakDeadTimeConfig.DeadTime = 0;
  sBreakDeadTimeConfig.BreakState = TIM_BREAK_DISABLE;
  sBreakDeadTimeConfig.BreakPolarity = TIM_BREAKPOLARITY_HIGH;
  sBreakDeadTimeConfig.BreakFilter = 0;
  sBreakDeadTimeConfig.Break2State = TIM_BREAK2_DISABLE;
  sBreakDeadTimeConfig.Break2Polarity = TIM_BREAK2POLARITY_HIGH;
  sBreakDeadTimeConfig.Break2Filter = 0;
  sBreakDeadTimeConfig.AutomaticOutput = TIM_AUTOMATICOUTPUT_DISABLE;
  if (HAL_TIMEx_ConfigBreakDeadTime(&htim1, &sBreakDeadTimeConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM1_Init 2 */

  /* USER CODE END TIM1_Init 2 */
  HAL_TIM_MspPostInit(&htim1);

}

/**
  * @brief TIM16 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM16_Init(void)
{

  /* USER CODE BEGIN TIM16_Init 0 */

  /* USER CODE END TIM16_Init 0 */

  /* USER CODE BEGIN TIM16_Init 1 */

  /* USER CODE END TIM16_Init 1 */
  htim16.Instance = TIM16;
  htim16.Init.Prescaler = 72-1;
  htim16.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim16.Init.Period = 65535;
  htim16.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim16.Init.RepetitionCounter = 0;
  htim16.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim16) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM16_Init 2 */

  /* USER CODE END TIM16_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 38400;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  huart2.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * Enable DMA controller clock
  */
static void MX_DMA_Init(void)
{

  /* DMA controller clock enable */
  __HAL_RCC_DMA1_CLK_ENABLE();

  /* DMA interrupt init */
  /* DMA1_Channel1_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA1_Channel1_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA1_Channel1_IRQn);
  /* DMA1_Channel2_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA1_Channel2_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA1_Channel2_IRQn);

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, LD2_Pin|GPIO_PIN_8|GPIO_PIN_9|GPIO_PIN_10, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10|GPIO_PIN_4, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_7, GPIO_PIN_RESET);

  /*Configure GPIO pin : B1_Pin */
  GPIO_InitStruct.Pin = B1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(B1_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pins : LD2_Pin PA8 PA9 PA10 */
  GPIO_InitStruct.Pin = LD2_Pin|GPIO_PIN_8|GPIO_PIN_9|GPIO_PIN_10;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /*Configure GPIO pins : PB10 PB4 */
  GPIO_InitStruct.Pin = GPIO_PIN_10|GPIO_PIN_4;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /*Configure GPIO pin : PC7 */
  GPIO_InitStruct.Pin = GPIO_PIN_7;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

}

/* USER CODE BEGIN 4 */
void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef* hadc){
	HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, SET);
}
/*void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}*/
void changeSampling(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_601CYCLES_5);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock1(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_1);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock2(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_2);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock4(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_4);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock6(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_6);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock8(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_8);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock10(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_10);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock12(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_12);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock16(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_16);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock32(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_32);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock64(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_64);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock128(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_128);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeADC1Clock256(){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_RCC_SetADCClockSource(LL_RCC_ADC12_CLKSRC_PLL_DIV_256);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}

void changeSampling0(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_1CYCLE_5);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeSampling1(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_2CYCLES_5);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeSampling2(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_4CYCLES_5);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeSampling3(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_7CYCLES_5);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeSampling4(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_19CYCLES_5);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeSampling5(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_61CYCLES_5);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeSampling6(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_181CYCLES_5);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
void changeSampling7(ADC_HandleTypeDef* hadc){
	HAL_ADC_Stop_DMA(&hadc1);
	LL_ADC_SetChannelSamplingTime(ADC1, LL_ADC_CHANNEL_1,LL_ADC_SAMPLINGTIME_601CYCLES_5);
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buff, ADC_BUFF);
}
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
