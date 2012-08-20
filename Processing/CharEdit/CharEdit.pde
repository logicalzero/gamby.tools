final static int CHAR_HEIGHT = 5;
final static int CHAR_WIDTH = 5;
final static int CHAR_SIZE = CHAR_HEIGHT * CHAR_WIDTH + 2;  // number of bytes used by a character in the editor. The 2 is the w/h offset.
final static int CHAR_COUNT = 160; //162; // skip first 32

final static int DRAW_SIZE = 32;

int charsetDrawY = 160 + (CHAR_HEIGHT * DRAW_SIZE);
int charsetColumns;

String[] sampleText = {
  "Pack my box with: five dozen brown liquor jugs. The quick brown fox jumps over the lazy god?",
  "Pack my box with: five dozen brown liquor jugs. Waltz, nymph, for quick jigs vex bud.",
  "for (i=0; i<42; i++) { printf(\"Hello World!\\n\"); }",
  "for (i=0; i<42; i++) { printf(\"Hello World!\\n\"); }",
  "Now is the time for all good men to come to the aid of their country!",
  "This is what I believe: rocks are hard; air is soft; and blue is usually a color! Right?"
};

String[][] helpText = {
  {"arrows:\n[,] and [.]:\n[-] and [=]:\n[o]:\n[s]:\n[a]:\n[x]:", "pick character\nset width\nset baseline\nopen file...\nsave font\nsave as...\nexport\n(print to console)"},
  {"[X]:\n\n[b]:\n\n[B]:", "export in rows/\ncolumns order\nexport as bytes\n(columns/rows)\nexport as bytes\n(rows/columns)"}
};

String dataFile = "characters.dat";
boolean changesMade = false;
int helpPage = 0;

PFont font;

// 0: character
// 1: rows
// 2: columns
byte[] chars;
int currentChar;

int clickedX, clickedY, clickedIdx, hoverIdx;
int textX, textY;

//
// getCharPixel: Get single pixel of a character in its local 5x5 grid.
// idx:  the character index (ASCII - 32)
// x, y:  position
//
boolean getCharPixel (int idx, int x, int y) {
  if (chars[(idx * CHAR_SIZE) + (y * CHAR_WIDTH) + x] == 1) return true;
  else return false;
}

//
// setCharPixel(): Set the value of a specific pixel of a character.
//
void setCharPixel (int idx, int x, int y, boolean pixel) {
  byte b = 0;
  if (pixel) b = 1;
  chars[(idx * CHAR_SIZE) + (y * CHAR_WIDTH) + x] = b;
}


//
// toggleCharPixel(): Flip a character's pixel.
//
void toggleCharPixel (int idx, int x, int y) {
  int pIdx = (idx * CHAR_SIZE) + (y * CHAR_WIDTH) + x;
  clickedIdx = pIdx;
  if (chars[pIdx] == 0) chars[pIdx] = 1;
  else chars[pIdx] = 0;
}


//
// getCharWidth(): Retrieces a character's width. Note: because of earlier experiments,
// this is actually (max character width) - (actual width), so a 1-pixel-wide character
// will have a width of 4.
//
byte getCharWidth (int idx) {
  return chars[((idx + 1) * CHAR_SIZE - 2)];
}


//
// incCharWidth(): Adjusts a character's width.
//
void incCharWidth (int idx, int inc) {
  int w = ((idx + 1) * CHAR_SIZE - 2);
  chars[w] += inc;
  if (chars[w] > CHAR_WIDTH) chars[w] = CHAR_WIDTH;
  else if (chars[w] < 0) chars[w] = 0;
}


//
// getCharBaseline(): Retrieves the character's baseline (the vertical offset).
//
byte getCharBaseline (int idx) {
  return chars[((idx + 1) * CHAR_SIZE - 1)];
}


//
// incCharBaseline(): Adjusts a character's baseline.
//
void incCharBaseline (int idx, int inc) {
  int h = ((idx + 1) * CHAR_SIZE - 1);
  chars[h] += inc;
  if (chars[h] > CHAR_HEIGHT) chars[h] = CHAR_HEIGHT;
  else if (chars[h] < 0) chars[h] = 0;
}

//
// drawChar(): Draws a character for editing.
//
void drawChar (int charIdx, int offsetX, int offsetY, int scalar, boolean outline, boolean back) {
  int i,j,x,y, thisIdx;
  
  for (i = 0; i < CHAR_HEIGHT; i++) {
    y = scalar * i + offsetY;
    for (j = 0; j < CHAR_WIDTH; j++) {
      x = scalar * j + offsetX;
      thisIdx = (charIdx * CHAR_SIZE) + (i * CHAR_WIDTH) + j;
      
      if (back) {
        if ((mouseX >= x) && (mouseX < x + scalar) && (mouseY >= y) && (mouseY < y + scalar)) {
          if (chars[thisIdx] == 0) fill(255,255,200);
          else fill(32);
        }
        else {
          if (chars[thisIdx] == 0) fill(240);
          else fill(0);
        }
      }
      else if (chars[thisIdx] == 0) noFill();
       else fill(0);
        
      if (outline) stroke(128, 16);
      else noStroke();
      
      rect(x,y,scalar,scalar);
    }
  }
}


//
// drawVertOffset(): Draws the vertical offset marker on the editing grid.
//
void drawVertOffset () {
  int h = DRAW_SIZE * (CHAR_HEIGHT - getCharBaseline(currentChar)) + 40;
  int w = DRAW_SIZE * (CHAR_WIDTH - getCharWidth(currentChar)) + 40;
  int halfHeight = DRAW_SIZE / 2;
  int drawSize = CHAR_HEIGHT * DRAW_SIZE;
  
  noStroke();
  
  fill(0,0,255);
  stroke(0,0,255,48);
  line(40,h,drawSize+40,h);
  triangle(
    10, (h + 6), 
    35, (h), 
    10, (h - 6));
  
  fill(190,0,200);
  stroke(190,0,200,48);
  line(w,40,w,drawSize+40);
  triangle( 
    (w + 6), (65 + drawSize), 
    (w), (45 + drawSize), 
    (w - 6), (65 + drawSize)); 
}


//
// drawCharset(): Draw the whole character set across the bottom of the screen.
// Also handles highlighting the character under the mouse cursor and boxing the
// current character.
//
void drawCharset ()
{
  int x = 40;
  int y = charsetDrawY;
  
  hoverIdx = -1;
  noFill();
      
  for (int i = 0; i < CHAR_COUNT; i++) {
    if (x > width - 40) {
      x = 40;
      y += (4 * CHAR_HEIGHT);
    }
    
    if (i == currentChar) {
      strokeWeight(2);
      stroke(64,64,255);
      rect(x - 4, y - 4, CHAR_WIDTH * 2 + 8, CHAR_HEIGHT * 2 + 8);
    }
    
    if ((mouseX > x) && (mouseY > y) && (mouseX <= x + CHAR_WIDTH * 2) && (mouseY <= y + CHAR_HEIGHT * 2)) {
      strokeWeight(2);
      stroke(255,255,64);
      rect(x - 4, y - 4, CHAR_WIDTH * 2 + 8, CHAR_HEIGHT * 2 + 8);
      hoverIdx = i;
    }
    
    drawChar (i, x, y, 2, false, false);
    x += (4 * CHAR_WIDTH);
  }
}


//
// drawText(): Draws a character in the current font at the current text coordinates.
// The X position is increased by the width of the character.
//
void drawText (char ch, int scalar) {
  int idx = ((int)ch) - 32;
  drawChar(idx, textX, (textY + (getCharBaseline(idx)) * scalar), scalar, false, false);
  textX += (1 + CHAR_WIDTH - getCharWidth(idx)) * scalar;
}


//
// drawText(): Draws a character using the current font at the given screen
// coordinates.
//
void drawText (char ch, int x, int y, int scalar) {
  textX = x;
  textY = y;
  drawText(ch, scalar);
}


//
// drawText(): Draws a string using the current font at the given screen
// coordinates.
//
void drawText (String s, int x, int y, int scalar) {
  int l = s.length();
  textX = x;
  textY = y;
  
  for (int i = 0; i < l; i++) {
    drawText(s.charAt(i), scalar);
  }
}


//
// setup(): Let's rock and roll.
// Standard Processing function.
//
void setup () {
  font = loadFont("AUdimat-Bold-16.vlw");
  textFont(font, 16);
  
  size(700,440);
  frameRate(15);
  
  chars = new byte[CHAR_COUNT * (CHAR_HEIGHT + 2) * CHAR_WIDTH];
  charsetColumns = (width - 80) / (CHAR_WIDTH * 4) + 1;
  currentChar = 0;

  loadCharSet();
}


//
// draw(): The main drawing loop.
// Standard Processing function.
//
void draw () {
  background(255);
  fill(0);
  text("Editing '" + char(currentChar + 32) + "' (char " + (currentChar + 32) + ")", 20, 20);
  textAlign(RIGHT);
  String modMark = "\0";
  if (changesMade)
    modMark = "*";
  if (dataFile.equals("characters.dat"))
    text("<sketch folder>/data/characters.dat (default font)" + modMark, width-20, 20);
   else
     text(dataFile + modMark, width-20, 20);
   textAlign(LEFT);
  
  int x1 = 60 + (1 + CHAR_WIDTH * DRAW_SIZE);
  int x2 = 20 + x1 + (1 + CHAR_WIDTH * DRAW_SIZE / 2);
  int x3 = 20 + x2 + (1 + CHAR_WIDTH * DRAW_SIZE / 4);
  int x4 = 20 + x3 + (1 + CHAR_WIDTH * DRAW_SIZE / 8);
  int x5 = 20 + x4 + (1 + CHAR_WIDTH * 2);
  
  drawChar(currentChar, 40, 40, DRAW_SIZE, true, true);
  drawVertOffset();
  drawChar(currentChar, x1, 40, DRAW_SIZE / 2, true, true);
  drawChar(currentChar, x2, 40, DRAW_SIZE / 4, false, true);
  drawChar(currentChar, x3, 40, DRAW_SIZE / 8, false, true);
  drawChar(currentChar, x4, 40, 2, false, true);
  drawChar(currentChar, x5, 40, 1, false, true);

  fill(0);
  // Due to an earlier experiment, character widths are stored as (char width) - width
  text("baseline: " + getCharBaseline(currentChar) + "\nwidth: " + (CHAR_WIDTH - getCharWidth(currentChar)), x1, 180);
  
  drawCharset();
  drawText(sampleText[0], 20,240,1);
  drawText(sampleText[1], 20, 250, 2);
  drawText(sampleText[2], 20, 270, 1);
  drawText(sampleText[3], 20, 280, 2);

  // Draw help box
  // box drop shadow - just for laffs.
  fill(0,32);  
  rect(474,35,width-485,208);
  // box proper
  fill(196);
  rect(470,30,width-485,208);
  // title drop shadow - also for yuks.
  fill(150);
  text("keys:   (? for more)", 482,57);
  // title proper
  fill(255);
  text("keys:   (? for more)", 480,55);

  // key to the keys
  fill(64);  
  textAlign(RIGHT);
  text(helpText[helpPage][0], 550,72);
  textAlign(LEFT);
  text(helpText[helpPage][1], 560,72);  
}


//
//
// Standard Processing function.
//
void mouseReleased () {
  if (hoverIdx > -1) {
    currentChar = hoverIdx;
  }
  else if ((mouseX > 40) && (mouseX < (DRAW_SIZE * CHAR_WIDTH) + 40)) {
    if ((mouseY > 40) && (mouseY < (DRAW_SIZE * CHAR_HEIGHT) + 40)) {
      int x = (mouseX - 40) / DRAW_SIZE;
      int y = (mouseY - 40) / DRAW_SIZE;
      toggleCharPixel(currentChar, x, y);
      clickedX = x;
      clickedY = y;
      changesMade = true;
    }
  }
}

void changeHelpPage() {
  helpPage++;
  if (helpPage > 1)
    helpPage = 0;
}

//
// keyPressed(): Handle keyboard input.
// Standard Processing function.
//
void keyPressed ()
{
  switch (keyCode)
  {
    case LEFT: currentChar--; break;
    case RIGHT: currentChar++; break;
    case UP: currentChar -= charsetColumns; break;
    case DOWN: currentChar += charsetColumns; break;
    default: switch (key)
    {
      case 's': saveCharSet(); break;
      case ',': incCharWidth(currentChar, 1); changesMade = true; break;
      case '.': incCharWidth(currentChar, -1); changesMade = true; break;
      case '-': incCharBaseline(currentChar, 1); changesMade = true; break;
      case '=': incCharBaseline(currentChar, -1); changesMade = true; break;
      case 'x': exportCharSet(); break;
      case 'X': exportCharSet(false); break;
      case 'a': saveCharSetAs(); break;
      case 'o': openCharSet(); break;
      case 'b': exportCharSet(true, true); break;
      case 'B': exportCharSet(false, true); break;
      case '?': changeHelpPage(); break;
    }
  }
  if (currentChar < 0) currentChar = CHAR_COUNT - 1;
  else if (currentChar >= CHAR_COUNT) currentChar = 0; 
}


//
// saveCharSet(): Write the character set data file.
//
void saveCharSet() {
  saveBytes(dataFile, chars);
  changesMade = false;
}

void saveCharSetAs() {
  String f = selectOutput();
  if (f != null) {
    dataFile = f;
    saveCharSet();
  }
}

//
// loadCharSet(): Load the character set from the data file.
//
void loadCharSet() {
  chars = loadBytes(dataFile);
  changesMade = false;
}


void openCharSet() {
  String f = selectInput();
  if (f != null) {
    dataFile = f;
    loadCharSet();
  }
}

//
// exportCharSet(): Prints Arduino code to the console for copying and pasting into a sketch.
//
void exportCharSet () {
  exportCharSet(true, false);
}

void exportCharSet (boolean arduinoStyle) {
  exportCharSet(arduinoStyle, false);
}

void exportCharSet (boolean arduinoStyle, boolean asBytes) {
  int charBitmapSize = CHAR_WIDTH * CHAR_HEIGHT;
  
  print("// Font generated from ");
  if (dataFile.equals("characters.dat"))
    println("<CharEdit sketch folder>/data/characters.dat (default font)");
   else
     println(dataFile);
  
  if (arduinoStyle)
    println("// Each character is 32 bits:\n//  bits 0-24: the character bitmap (by column)\n//  bits 25-27: character vertical offset\n//  bits 28-31: character width");
  else
    println("// Each character is 32 bits:\n//  bits 0-24: the character bitmap (by row)\n//  bits 25-27: character vertical offset\n//  bits 28-31: character width\n{");
    
  if (asBytes)
    println ("PROGMEM prog_uchar font[] = {");
  else
    println ("PROGMEM prog_uint32_t font[] = {");
    
  for (int i = 0; i < CHAR_COUNT; i++) {
    int charIdx = i * CHAR_SIZE;
    int vertOffset = getCharBaseline(i);
    int charWidth = getCharWidth(i);
    int c = 0;
    
    // Get the character's bitmap
    if (arduinoStyle) {
      // Bitmap defined in columns for use with GoldLCD
      for (int j = 0; j < CHAR_WIDTH; j++) {
        for (int k = 0; k < CHAR_HEIGHT; k++) {
          if (getCharPixel(i, j, CHAR_HEIGHT-k-1))
            c = c | 1;
          c = (c << 1);
        }
      }
    }
    else {
      // Bitmap defined in rows (as usual)
      for (int j = 0; j < CHAR_HEIGHT; j++) {
        for (int k = 0; k < CHAR_WIDTH; k++) {

          if (getCharPixel(i, k, j))
            c = c | 1;
          c = (c << 1);
        }
      }
    }

    // Add in the vertical offset
    c = (c << 2) | (vertOffset & 0x07); // already shifted by 1
    c = (c << 4) | ((5-charWidth) & 0x0F);
    
    if (asBytes)    {
      for (int k = 3; k >= 0; k--) {
        print("0x" + hex((c >> (k * 8)) & 0xFF).substring(6));
        if (!(k == 0 && i == CHAR_COUNT - 1))
          print(", ");
        else
          print("  ");
      }
    }
    else
      print("  0x" + hex(c) + "L,");

    println("    // character '" + str(char(i + 32)) + "' (" + str(i + 32) + ")");
  }
  println("};");
}
