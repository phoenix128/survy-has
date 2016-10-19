#define TYPE_433MHZ 0
#define TYPE_868MHZ 1
#define TYPE_MAX 2

#define IRQ_433MHZ 0 // Pin 2
#define IRQ_868MHZ 1 // Pin 3
#define PIN_OUT_433MHZ 4
#define PIN_OUT_868MHZ 5

#define MAX_BUFFER_SIZE 128
#define IN_BUFFER_SIZE 512 // MAX_BUFFER_SIZE x 4
#define BAUD_RATE 115200
#define OUT_SIGNAL_REPETITION 3
#define OUT_SIGNAL_BREAK_MULTIPLIER 4
#define RESOLUTION_FACTOR 10

#define MIN_SIGNAL_TIME 10 // Set 100us as min pulse time
#define BREAK_TIME 2000 // Interval between a signal sequence and the other

uint32_t signal_change_ts[TYPE_MAX];
uint32_t last_signal_change_ts[TYPE_MAX];

uint16_t buffer[TYPE_MAX][MAX_BUFFER_SIZE];
uint8_t buffer_pos[TYPE_MAX];
uint8_t pin_out[TYPE_MAX];

char signal_desc[TYPE_MAX][4];
bool data_ready[TYPE_MAX];
bool triggered[TYPE_MAX];

char buffer_in[IN_BUFFER_SIZE];
uint16_t buffer_in_pos;

int serial_putc(char c, FILE*)
{
  Serial.write(c);
  return c;
}

void printf_begin(void)
{
  fdevopen(&serial_putc, 0);
}

void irq_433mhz() {
  register_signal(TYPE_433MHZ);
}

void irq_868mhz() {
  register_signal(TYPE_868MHZ);
}

void reset_buffer(uint8_t type) {
  buffer_pos[type] = 0;
  data_ready[type] = 0;
  triggered[type] = false;
  last_signal_change_ts[type] = micros();
}

void flush_buffer(uint8_t type) {
  uint16_t min_high=0;
  uint16_t min_low=0;
  uint16_t max_high=0;
  uint16_t max_low=0;
  uint16_t middle_high;
  uint16_t middle_low;

  char current_signal_pattern[MAX_BUFFER_SIZE];

  if ((buffer_pos[type] > 24) && (((buffer_pos[type]-1) % 24) == 0)){ // 24 = 8bit x3

    // Search min and max
    for (uint16_t i=0; i<buffer_pos[type]; i++)
    {
      if (i % 2) // LOW
      {
        if (!min_low || (buffer[type][i] < min_low)) min_low = buffer[type][i];
        if (!max_low || (buffer[type][i] > max_low)) max_low = buffer[type][i];
      }
      else // HIGH
      {
        if (!min_high || (buffer[type][i] < min_high)) min_high = buffer[type][i];
        if (!max_high || (buffer[type][i] > max_high)) max_high = buffer[type][i];
      }
    }

    middle_high = (max_high + min_high) / 2;
    middle_low = (max_low + min_low) / 2;

    // Print pattern
    uint16_t val = 0;
    uint16_t c = 0;

    for (uint16_t i=0; i<buffer_pos[type]; i++)
    {
      uint16_t ref = (i % 2) ? middle_low : middle_high;
      val <<= 1;
      val |= (buffer[type][i] > ref) ? 1 : 0;

      if (((i % 16) == 15) || (i == buffer_pos[type]-1))
      {
        printf("%04x", val);
        c++;
        val=0;
      }
    }
    
    printf(":");
    
    // Print signals sequence
    for (uint8_t i=0; i<buffer_pos[type]; i++) {
      printf("%03x", buffer[type][i]/RESOLUTION_FACTOR);
    }

    printf("\n");
  }

  reset_buffer(type);
}

void register_signal(uint8_t type) {
  signal_change_ts[type] = micros();

  if (!data_ready[type]) {

    uint32_t delta = signal_change_ts[type] - last_signal_change_ts[type];
    last_signal_change_ts[type] = signal_change_ts[type];

    if (delta < MIN_SIGNAL_TIME) return; // Radio pulse is too short

    if ((buffer_pos[type] > 0) && (delta > BREAK_TIME)) {
      data_ready[type] = true; // We have got mail!

    } else if (delta > BREAK_TIME) {
      triggered[type] = true; // Possible signal

    } else if (triggered[type]) {
      buffer[type][buffer_pos[type]] = delta;
      buffer_pos[type]++;

      if (buffer_pos[type] >= MAX_BUFFER_SIZE) {
        reset_buffer(type); // Garbage
      }
    }
  }
}

void setup() {
  Serial.begin(BAUD_RATE);
  printf_begin();
  Serial.println("READY");

  pin_out[TYPE_433MHZ] = PIN_OUT_433MHZ;
  pin_out[TYPE_433MHZ] = PIN_OUT_433MHZ;

  for (uint8_t i=0; i<TYPE_MAX; i++) {
    reset_buffer(i);

    pinMode(pin_out[i], OUTPUT);
    digitalWrite(pin_out[i], LOW);
  }
  
  enable_receive(true);
}

void enable_receive(bool status) {
  if (status) {
    for (uint8_t i=0; i<TYPE_MAX; i++)
      reset_buffer(i);
    
    attachInterrupt(IRQ_433MHZ, irq_433mhz, CHANGE);
    attachInterrupt(IRQ_868MHZ, irq_868mhz, CHANGE);
  } else {
    detachInterrupt(IRQ_433MHZ);
    detachInterrupt(IRQ_868MHZ);
  }
}

void send_signal(bool status, uint16_t value) {
  for (uint8_t i=0; i<TYPE_MAX; i++) {
    digitalWrite(pin_out[i], status ? HIGH : LOW);
  }
  delayMicroseconds(value*RESOLUTION_FACTOR);
}

void send_signal_break(uint8_t multip) {
  for (uint8_t i=0; i<TYPE_MAX; i++) {
    digitalWrite(pin_out[i], LOW);
  }
  delayMicroseconds(BREAK_TIME*multip);
}

void parse_incoming() {
  char *signal_dump;
  uint16_t signal_buffer[MAX_BUFFER_SIZE];
  uint8_t signal_buffer_pos = 0;

  uint8_t i = 0;
  signal_dump = buffer_in;

  for (uint16_t i=0; i<strlen(signal_dump); i+=3) {
    char val[4];
    memcpy(val, signal_dump+i, 3); val[3] = '\0';
    signal_buffer[signal_buffer_pos++] = strtol(val, NULL, 16);
  }

  if (signal_buffer_pos > 0)
  {
    enable_receive(false);

    for (uint8_t break_multip=0; break_multip<OUT_SIGNAL_BREAK_MULTIPLIER; break_multip++) {
      for (uint16_t j=0; j<OUT_SIGNAL_REPETITION; j++) {
        
        for (uint16_t i=0; i<signal_buffer_pos; i++) {
          send_signal((i % 2) == 0, signal_buffer[i]);
        }
        send_signal_break(break_multip*2);
      }
    }
    
    printf("done\n");

    enable_receive(true);
  }

  buffer_in_pos = 0;
}

void loop() {
  for (uint8_t i=0; i<TYPE_MAX; i++) {
    if (data_ready[i]) flush_buffer(i);
  }

  while (Serial.available() > 0) {;
    char c = Serial.read();
    if (buffer_in_pos >= IN_BUFFER_SIZE) buffer_in_pos = 0;
    buffer_in[buffer_in_pos] = '\0';
    if (((c == '\n') || (c == '\r')) && (buffer_in_pos > 0)) {
      parse_incoming();
    } else {
      buffer_in[buffer_in_pos++] = c;
    }
  }
}
