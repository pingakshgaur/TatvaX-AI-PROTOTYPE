import os
from typing import Dict
import re


class ContentManager:
    """Fixed content management for subjects and institutional FAQs"""

    def __init__(self):
        print("📚 Initializing Content Manager...")

        self.content_dir = "content_library"
        self.subjects_dir = os.path.join(self.content_dir, "subjects")
        self.institutional_dir = os.path.join(self.content_dir, "institutional")

        # Create directories if they don't exist
        os.makedirs(self.subjects_dir, exist_ok=True)
        os.makedirs(self.institutional_dir, exist_ok=True)

        # Subject information with proper file names
        self.subjects = {
            "mathematics": {
                "name": "Mathematics",
                "icon": "fas fa-calculator",
                "description": "Numbers, Algebra, Geometry, and Problem-solving",
                "color": "#3b82f6",
                "file": "content_library\\subjects\\mathematics-content.txt",
            },
            "science": {
                "name": "Science",
                "icon": "fas fa-flask",
                "description": "Physics, Chemistry, Biology, and Experiments",
                "color": "#10b981",
                "file": "content_library\\subjects\\science-content.txt",
            },
            "english": {
                "name": "English",
                "icon": "fas fa-book-open",
                "description": "Language, Literature, Grammar, and Writing",
                "color": "#f59e0b",
                "file": "content_library\\subjects\\english-content.txt",
            },
            "social_studies": {
                "name": "Social Studies",
                "icon": "fas fa-globe-asia",
                "description": "History, Geography, Civics, and Culture",
                "color": "#ef4444",
                "file": "content_library\\subjects\\social-studies-content.txt",
            },
        }

        # Initialize content files if they don't exist
        self.create_content_files_if_missing()

        print("✅ Content Manager initialized with 4 subjects and institutional FAQs")

    def get_available_subjects(self) -> Dict[str, Dict]:
        """Get all available subjects with metadata"""
        return self.subjects

    def load_subject_content(self, subject: str) -> str:
        """Load content for a specific subject"""
        try:
            if subject not in self.subjects:
                return f"Subject '{subject}' not found. Available subjects: {', '.join(self.subjects.keys())}"

            # Get the correct filename
            filename = self.subjects[subject]["file"]
            content_file = os.path.join(self.subjects_dir, filename)

            print(f"📖 Loading content from: {content_file}")

            if not os.path.exists(content_file):
                print(f"❌ File not found: {content_file}")
                return self.create_fallback_content(subject)

            with open(content_file, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                print(f"⚠️ Empty content file: {content_file}")
                return self.create_fallback_content(subject)

            print(f"✅ Loaded {subject} content: {len(content)} characters")
            return content

        except Exception as e:
            print(f"❌ Error loading {subject} content: {e}")
            return self.create_fallback_content(subject)

    def load_institutional_content(self) -> str:
        """Load institutional FAQ content"""
        try:
            content_file = os.path.join(
                self.institutional_dir,
                "content_library\\institutional\\faqs-responses.txt",
            )

            print(f"🏫 Loading institutional content from: {content_file}")

            if not os.path.exists(content_file):
                print(f"❌ Institutional file not found: {content_file}")
                return self.create_fallback_institutional_content()

            with open(content_file, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                print(f"⚠️ Empty institutional content file")
                return self.create_fallback_institutional_content()

            print(f"✅ Loaded institutional content: {len(content)} characters")
            return content

        except Exception as e:
            print(f"❌ Error loading institutional content: {e}")
            return self.create_fallback_institutional_content()

    def find_relevant_content(
        self, query: str, content: str, max_sentences: int = 5
    ) -> str:
        """Find relevant content sections based on query"""
        try:
            if not content or not content.strip():
                return "No content available for this topic."

            query_words = set(query.lower().split())

            # Split content into paragraphs first, then sentences
            paragraphs = content.split("\n\n")

            scored_sections = []

            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue

                # Check if paragraph contains relevant keywords
                paragraph_lower = paragraph.lower()
                overlap = len(query_words.intersection(set(paragraph_lower.split())))

                if overlap > 0:
                    # Clean the paragraph
                    clean_paragraph = self.clean_content(paragraph)
                    if clean_paragraph:
                        scored_sections.append((clean_paragraph, overlap))

            # Sort by relevance and take top sections
            scored_sections.sort(key=lambda x: x[1], reverse=True)

            if scored_sections:
                # Take top sections and combine them
                top_sections = [
                    s[0] for s in scored_sections[:3]
                ]  # Take top 3 most relevant sections
                result = "\n\n".join(top_sections)
                print(
                    f"🎯 Found {len(scored_sections)} relevant sections, returning top 3"
                )
                return result
            else:
                # If no specific match, return first few meaningful paragraphs
                meaningful_paragraphs = []
                for paragraph in paragraphs[:5]:  # Take first 5 paragraphs
                    clean_paragraph = self.clean_content(paragraph)
                    if (
                        clean_paragraph and len(clean_paragraph) > 50
                    ):  # Only substantial paragraphs
                        meaningful_paragraphs.append(clean_paragraph)

                if meaningful_paragraphs:
                    result = "\n\n".join(meaningful_paragraphs)
                    print(f"📝 Using first meaningful paragraphs")
                    return result
                else:
                    # Final fallback
                    return content[:1000] if len(content) > 1000 else content

        except Exception as e:
            print(f"❌ Error finding relevant content: {e}")
            return content[:1000] if content else "Content not available."

    def clean_content(self, text: str) -> str:
        """Clean content for better presentation"""
        try:
            if not text:
                return ""

            # Remove excessive markdown headers for cleaner presentation
            text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

            # Keep basic formatting
            # Remove extra whitespace but keep paragraph breaks
            lines = text.split("\n")
            cleaned_lines = []

            for line in lines:
                cleaned_line = line.strip()
                if cleaned_line:
                    cleaned_lines.append(cleaned_line)
                elif cleaned_lines and cleaned_lines[-1]:  # Preserve paragraph breaks
                    cleaned_lines.append("")

            # Join lines back
            cleaned_text = "\n".join(cleaned_lines)

            # Remove excessive newlines
            cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

            return cleaned_text.strip()

        except Exception as e:
            print(f"❌ Error cleaning content: {e}")
            return text

    def create_content_files_if_missing(self):
        """Create content files with minimal content if they don't exist"""

        # Check and create subject files
        for subject_key, subject_info in self.subjects.items():
            filename = subject_info["file"]
            filepath = os.path.join(self.subjects_dir, filename)

            if not os.path.exists(filepath):
                print(f"📝 Creating missing file: {filename}")
                content = self.create_fallback_content(subject_key)
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"✅ Created {filename}")
                except Exception as e:
                    print(f"❌ Error creating {filename}: {e}")

        # Check and create institutional file
        institutional_file = os.path.join(self.institutional_dir, "faq_responses.txt")
        if not os.path.exists(institutional_file):
            print(f"📝 Creating missing institutional file")
            content = self.create_fallback_institutional_content()
            try:
                with open(institutional_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ Created faq_responses.txt")
            except Exception as e:
                print(f"❌ Error creating institutional file: {e}")

    def create_fallback_content(self, subject: str) -> str:
        """Create fallback content for subjects"""

        fallback_contents = {
            "mathematics": """
            # MATHEMATICS - Complete Learning Guide

## Chapter 1: Number System

**Natural Numbers**
Natural numbers are counting numbers starting from 1, 2, 3, 4, and so on.
These are the first numbers we learn to count with.
Examples: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10...

**Whole Numbers**  
Whole numbers include all natural numbers plus zero.
Set of whole numbers: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10...
Zero is the smallest whole number.

**Integers**
Integers include positive numbers, negative numbers, and zero.
Examples: ...-3, -2, -1, 0, 1, 2, 3...
Positive integers: 1, 2, 3, 4...
Negative integers: -1, -2, -3, -4...

**Rational Numbers**
Rational numbers can be expressed as fractions where denominator is not zero.
Examples: 1/2, 3/4, -2/5, 0.5, 0.75
Every integer is also a rational number.

**Irrational Numbers**
Numbers that cannot be expressed as fractions.
Examples: π (pi), √2, √3, e
These have non-terminating, non-repeating decimal expansions.

## Chapter 2: Basic Operations

**Addition**
Addition means combining two or more numbers to get their sum.
Symbol: + (plus sign)
Example: 5 + 3 = 8
Properties:
- Commutative: a + b = b + a
- Associative: (a + b) + c = a + (b + c)
- Identity: a + 0 = a

**Subtraction**
Subtraction means finding the difference between two numbers.
Symbol: - (minus sign)
Example: 8 - 3 = 5
Subtraction is the inverse operation of addition.

**Multiplication**
Multiplication is repeated addition or finding the product of numbers.
Symbol: × or * (times sign)
Example: 4 × 3 = 12 (which is 4 + 4 + 4)
Properties:
- Commutative: a × b = b × a
- Associative: (a × b) × c = a × (b × c)
- Identity: a × 1 = a
- Zero property: a × 0 = 0

**Division**
Division is splitting a number into equal parts.
Symbol: ÷ or / (division sign)
Example: 12 ÷ 3 = 4
Division is the inverse operation of multiplication.

## Chapter 3: BODMAS Rule

**Order of Operations**
BODMAS stands for:
- **B**rackets
- **O**rders (powers and roots)
- **D**ivision
- **M**ultiplication
- **A**ddition
- **S**ubtraction

**How to Use BODMAS**
1. First solve operations inside Brackets ( )
2. Then solve Orders (powers like 2², roots like √9)
3. Then solve Division and Multiplication from left to right
4. Finally solve Addition and Subtraction from left to right

**Example:**
Solve: 2 + 3 × 4 - 1
Step 1: No brackets or orders
Step 2: Multiplication first: 3 × 4 = 12
Step 3: Now we have: 2 + 12 - 1
Step 4: Left to right: 2 + 12 = 14, then 14 - 1 = 13
Answer: 13

## Chapter 4: Fractions

**What is a Fraction?**
A fraction represents part of a whole.
Written as numerator/denominator
Example: 3/4 means 3 parts out of 4 equal parts

**Types of Fractions**
- **Proper fraction**: Numerator < Denominator (3/5, 2/7)
- **Improper fraction**: Numerator ≥ Denominator (7/5, 8/3)
- **Mixed number**: Whole number + proper fraction (2 1/3, 1 3/4)

**Adding Fractions**
- **Like fractions** (same denominator): Add numerators, keep denominator
  Example: 2/7 + 3/7 = 5/7
- **Unlike fractions** (different denominators): Find common denominator first
  Example: 1/3 + 1/4 = 4/12 + 3/12 = 7/12

**Subtracting Fractions**
Follow same rules as addition but subtract numerators.
Example: 5/6 - 2/6 = 3/6 = 1/2

**Multiplying Fractions**
Multiply numerators together and denominators together.
Example: 2/3 × 3/4 = 6/12 = 1/2

**Dividing Fractions**
Multiply by the reciprocal of the second fraction.
Example: 2/3 ÷ 1/4 = 2/3 × 4/1 = 8/3

## Chapter 5: Decimals

**Understanding Decimals**
Decimals use place value system with decimal point.
Place values after decimal: tenths, hundredths, thousandths

**Example: 25.347**
- 2 is in tens place
- 5 is in ones place
- 3 is in tenths place
- 4 is in hundredths place
- 7 is in thousandths place

**Converting Fractions to Decimals**
Divide numerator by denominator.
Example: 3/4 = 3 ÷ 4 = 0.75

**Adding and Subtracting Decimals**
Align decimal points vertically.
Example:
  25.6
+ 13.47
-------
  39.07

**Multiplying Decimals**
1. Multiply as if they were whole numbers
2. Count total decimal places in both numbers
3. Place decimal point in answer

Example: 2.5 × 1.3
25 × 13 = 325
Total decimal places: 1 + 1 = 2
Answer: 3.25

## Chapter 6: Percentages

**What is Percentage?**
Percent means "per hundred" or "out of 100"
Symbol: %
Example: 25% = 25/100 = 0.25

**Converting Between Forms**
- Fraction to percentage: Multiply by 100
  Example: 3/4 = (3/4) × 100 = 75%
- Percentage to fraction: Divide by 100
  Example: 40% = 40/100 = 2/5
- Decimal to percentage: Multiply by 100
  Example: 0.6 = 0.6 × 100 = 60%

**Finding Percentage of a Number**
To find x% of a number: Multiply the number by x/100
Example: 20% of 50 = (20/100) × 50 = 10

**Applications**
- Calculating discounts in shopping
- Finding profit and loss in business
- Calculating marks and grades
- Interest calculations

## Chapter 7: Basic Algebra

**What is Algebra?**
Algebra uses letters and symbols to represent unknown numbers.
These letters are called variables or unknowns.
Common variables: x, y, z, a, b, c

**Algebraic Expressions**
Combination of numbers, variables, and operations.
Examples: 
- 3x + 5
- 2y - 7
- 4a + 3b - 2

**Terms in Algebra**
- **Constant**: Numbers without variables (5, -3, 10)
- **Variable**: Letters representing unknowns (x, y, z)
- **Coefficient**: Number multiplying a variable (in 5x, coefficient is 5)
- **Like terms**: Terms with same variables (3x and 7x)
- **Unlike terms**: Terms with different variables (3x and 5y)

**Simplifying Expressions**
Combine like terms by adding or subtracting coefficients.
Example: 3x + 5x - 2x = (3 + 5 - 2)x = 6x

**Simple Equations**
Equation shows two expressions are equal using = sign.
Example: x + 5 = 12
To solve: x = 12 - 5 = 7

## Chapter 8: Basic Geometry

**Points, Lines, and Angles**

**Point**
A point is an exact location with no size.
Represented by a dot and named with capital letters.
Example: Point A, Point B

**Line**
A straight path extending infinitely in both directions.
Has no thickness and no endpoints.
Named using two points on the line: Line AB

**Line Segment**
Part of a line with two endpoints.
Has definite length.
Example: Segment AB from point A to point B

**Ray**
Part of a line that starts at one point and extends infinitely in one direction.
Has one endpoint called origin.
Example: Ray AB starting from A

**Angle**
Formed when two rays meet at a common point called vertex.
Measured in degrees (°)

**Types of Angles**
- **Acute angle**: Less than 90°
- **Right angle**: Exactly 90°
- **Obtuse angle**: Between 90° and 180°
- **Straight angle**: Exactly 180°
- **Reflex angle**: Between 180° and 360°

## Chapter 9: Basic Shapes

**Triangle**
A polygon with three sides and three angles.
Sum of all angles in a triangle = 180°

**Types of Triangles by Sides**
- **Equilateral**: All three sides equal
- **Isosceles**: Two sides equal
- **Scalene**: All sides different

**Types of Triangles by Angles**
- **Acute triangle**: All angles less than 90°
- **Right triangle**: One angle equals 90°
- **Obtuse triangle**: One angle greater than 90°

**Quadrilaterals**
Polygons with four sides.
Sum of all angles = 360°

**Types of Quadrilaterals**
- **Square**: All sides equal, all angles 90°
- **Rectangle**: Opposite sides equal, all angles 90°
- **Rhombus**: All sides equal, opposite angles equal
- **Parallelogram**: Opposite sides parallel and equal
- **Trapezium**: One pair of parallel sides

**Circle**
All points equidistant from center.
- **Radius**: Distance from center to any point on circle
- **Diameter**: Line passing through center, touching circle at two points
- **Circumference**: Perimeter of circle

## Chapter 10: Measurement and Area

**Units of Length**
- Millimeter (mm): Smallest unit
- Centimeter (cm): 10 mm = 1 cm
- Meter (m): 100 cm = 1 m
- Kilometer (km): 1000 m = 1 km

**Area Formulas**
**Rectangle**: Area = length × width
**Square**: Area = side × side
**Triangle**: Area = (1/2) × base × height
**Circle**: Area = π × radius²

**Perimeter Formulas**
**Rectangle**: Perimeter = 2(length + width)
**Square**: Perimeter = 4 × side
**Triangle**: Perimeter = sum of all three sides
**Circle**: Circumference = 2π × radius

## Chapter 11: Data Handling

**Collecting Data**
Data is information collected about something.
Can be collected through surveys, observations, experiments.

**Organizing Data**
- **Tally marks**: Used for counting (||||)
- **Frequency**: How many times something appears
- **Tables**: Organize data in rows and columns

**Representing Data**
**Bar Graph**: Uses bars of different heights
- Helpful for comparing quantities
- Each bar represents a category

**Pie Chart**: Shows data as parts of a circle
- Each slice represents a part of the whole
- Useful for showing percentages

**Line Graph**: Shows how data changes over time
- Points connected by lines
- Good for showing trends

**Finding Average (Mean)**
Add all values and divide by number of values.
Example: Marks are 70, 80, 90
Average = (70 + 80 + 90) ÷ 3 = 240 ÷ 3 = 80

## Chapter 12: Problem Solving

**Steps to Solve Word Problems**
1. **Read carefully**: Understand what the problem is asking
2. **Identify given information**: What facts are provided?
3. **Find what needs to be calculated**: What is the question asking?
4. **Choose the operation**: Addition, subtraction, multiplication, or division?
5. **Solve step by step**: Work through the calculation
6. **Check your answer**: Does it make sense?

**Example Problem**
"Rahul has 45 marbles. He gives 12 marbles to his friend and buys 8 more. How many marbles does he have now?"

**Solution:**
- Given: Started with 45 marbles
- Gave away: 12 marbles
- Bought: 8 more marbles
- Calculation: 45 - 12 + 8 = 33 + 8 = 41
- Answer: Rahul has 41 marbles now

**Types of Problems**
- Money problems (buying, selling, change)
- Time problems (duration, schedules)
- Distance problems (speed, travel)
- Age problems (comparing ages)
- Sharing problems (dividing equally)

## Practice Tips

**Daily Practice**
- Solve at least 5 problems daily
- Practice mental math for quick calculations
- Use real-life situations to apply math concepts

**Understanding vs Memorizing**
- Focus on understanding concepts, not just memorizing formulas
- Ask "why" something works the way it does
- Connect new learning to what you already know

**Making Mistakes**
- Mistakes are part of learning
- Check your work carefully
- Learn from errors to avoid repeating them

**Getting Help**
- Ask questions when you don't understand
- Work with classmates to solve problems
- Use different methods to solve the same problem

Remember: Mathematics is everywhere in daily life. From calculating change at a shop to measuring ingredients for cooking, math helps us solve real problems!
            """,
            "science": """
            # SCIENCE - Complete Learning Guide

## Chapter 1: Introduction to Science

**What is Science?**
Science is the systematic study of the natural world through observation and experimentation.
It helps us understand how things work around us.
Science is divided into three main branches: Physics, Chemistry, and Biology.

**Scientific Method**
The scientific method is a step-by-step process used to investigate and understand natural phenomena.

**Steps of Scientific Method:**
1. **Observation**: Notice something interesting or unusual
2. **Question**: Ask a question about what you observed
3. **Hypothesis**: Make an educated guess to answer the question
4. **Experiment**: Test your hypothesis through controlled experiments
5. **Analysis**: Study the results of your experiment
6. **Conclusion**: Decide if your hypothesis was correct or not

**Importance of Science**
- Helps us understand the world around us
- Leads to new inventions and technologies
- Improves our quality of life
- Helps solve problems in medicine, agriculture, and environment

## Chapter 2: Matter and Its States

**What is Matter?**
Matter is anything that has mass and takes up space.
Everything around us is made of matter - air, water, rocks, plants, animals.

**Properties of Matter**
- **Mass**: Amount of matter in an object
- **Volume**: Amount of space an object occupies
- **Density**: Mass per unit volume

**Three States of Matter**

**1. Solid**
- Particles are tightly packed together
- Have definite shape and volume
- Particles vibrate but don't move around
- Examples: Ice, wood, metals, rocks

**2. Liquid**
- Particles are loosely packed
- Have definite volume but take shape of container
- Particles can move around each other
- Examples: Water, milk, oil, juice

**3. Gas**
- Particles are far apart and move freely
- No definite shape or volume
- Fill entire container
- Examples: Air, oxygen, carbon dioxide, steam

**Changes in States of Matter**
Matter can change from one state to another when heated or cooled.

- **Melting**: Solid to liquid (ice to water)
- **Freezing**: Liquid to solid (water to ice)
- **Evaporation**: Liquid to gas (water to steam)
- **Condensation**: Gas to liquid (steam to water)
- **Sublimation**: Solid directly to gas (dry ice to carbon dioxide gas)

## Chapter 3: Force and Motion

**What is Force?**
Force is a push or pull that can change the motion of an object.
Force can make objects start moving, stop moving, speed up, slow down, or change direction.

**Types of Forces**

**Contact Forces** (need to touch the object)
- **Muscular force**: Force applied by muscles (pushing a door)
- **Friction**: Force that opposes motion between two surfaces
- **Tension**: Force in a stretched rope or string

**Non-contact Forces** (work from a distance)
- **Gravitational force**: Earth pulls objects downward
- **Magnetic force**: Magnets attract or repel certain materials
- **Electrostatic force**: Force between charged objects

**Motion**
Motion is change in position of an object with time.

**Types of Motion**
- **Linear motion**: Motion in a straight line (car on straight road)
- **Circular motion**: Motion in a circle (wheel rotating)
- **Oscillatory motion**: Back and forth motion (pendulum)
- **Random motion**: Motion without fixed pattern (gas molecules)

**Speed**
Speed tells us how fast an object is moving.
Speed = Distance ÷ Time
Example: If a car travels 100 km in 2 hours, its speed is 50 km/h

## Chapter 4: Energy

**What is Energy?**
Energy is the ability to do work or cause change.
Energy cannot be created or destroyed, only changed from one form to another.

**Forms of Energy**

**1. Kinetic Energy**
- Energy of motion
- Moving objects have kinetic energy
- Examples: Running water, moving car, flying bird

**2. Potential Energy**
- Stored energy due to position or condition
- Examples: Water stored in dam, stretched rubber band, book on shelf

**3. Heat Energy**
- Energy that flows from hot objects to cold objects
- Makes things warm
- Examples: Sun, fire, hot stove

**4. Light Energy**
- Energy that helps us see
- Travels very fast in straight lines
- Examples: Sun, bulb, candle, stars

**5. Sound Energy**
- Energy that travels through vibrations
- Helps us hear
- Examples: Music, talking, bell ringing

**6. Electrical Energy**
- Energy from moving electric charges
- Powers our homes and devices
- Examples: Lightning, batteries, power plants

**Energy Transformations**
Energy changes from one form to another:
- Electric bulb: Electrical energy → Light energy + Heat energy
- Solar panel: Light energy → Electrical energy
- Microphone: Sound energy → Electrical energy
- Speaker: Electrical energy → Sound energy

## Chapter 5: Light

**Properties of Light**
- Light travels in straight lines
- Light travels very fast (300,000 km per second)
- Light can pass through transparent materials
- Light can be reflected (bounced off) by mirrors
- Light can be refracted (bent) when passing through different materials

**Sources of Light**
**Natural sources**: Sun, stars, fireflies, lightning
**Artificial sources**: Bulbs, candles, torches, LEDs

**How We See**
1. Light from a source falls on an object
2. The object reflects some of this light
3. Our eyes receive this reflected light
4. Our brain interprets this as seeing the object

**Shadows**
When light is blocked by an opaque object, a shadow is formed.
Shadow is always on the side opposite to the light source.
Size of shadow depends on:
- Distance of object from light source
- Distance of object from screen
- Size of light source

**Colors**
White light is made up of seven colors: Red, Orange, Yellow, Green, Blue, Indigo, Violet (ROYGBIV)
We can see this when white light passes through a prism - it splits into rainbow colors.
Objects appear colored because they reflect certain colors and absorb others.

## Chapter 6: Sound

**What is Sound?**
Sound is a form of energy that travels through vibrations.
All sounds are produced by vibrating objects.

**How Sound is Produced**
- Vibrating objects create sound waves
- These waves travel through air (or other materials)
- Our ears detect these vibrations as sound

**Properties of Sound**

**Pitch**
- How high or low a sound is
- Depends on frequency of vibrations
- Fast vibrations = High pitch (bird chirping)
- Slow vibrations = Low pitch (elephant trumpeting)

**Loudness**
- How loud or soft a sound is
- Depends on amplitude of vibrations
- Large vibrations = Loud sound
- Small vibrations = Soft sound

**Quality (Timbre)**
- What makes sounds different even at same pitch and loudness
- Helps us recognize different instruments or voices

**How Sound Travels**
- Sound needs a medium (air, water, solid) to travel
- Sound cannot travel through vacuum (empty space)
- Sound travels faster in solids than in liquids
- Sound travels faster in liquids than in gases

**Uses of Sound**
- Communication (talking, music)
- Echolocation (bats, dolphins)
- Medical diagnosis (ultrasound)
- Detecting objects (sonar)

## Chapter 7: Heat

**What is Heat?**
Heat is a form of energy that makes things warm.
Heat always flows from hot objects to cold objects.

**Sources of Heat**
- **Sun**: Main source of heat on Earth
- **Fire**: Burning produces heat
- **Friction**: Rubbing objects together
- **Electricity**: Electric heaters, bulbs
- **Chemical reactions**: Our body produces heat

**Effects of Heat**

**1. Change in Temperature**
- Adding heat increases temperature
- Removing heat decreases temperature

**2. Change in Size**
- Most objects expand (get bigger) when heated
- Most objects contract (get smaller) when cooled
- Railway tracks have gaps to allow expansion

**3. Change in State**
- Heat can change solids to liquids (melting)
- Heat can change liquids to gases (evaporation)

**Heat Transfer**
Heat moves from hot objects to cold objects in three ways:

**Conduction**
- Heat transfers through direct contact
- Common in solids
- Example: Metal spoon getting hot in hot soup

**Convection**
- Heat transfers through movement of fluids (liquids and gases)
- Example: Hot air rising, cold air sinking

**Radiation**
- Heat transfers through rays (without direct contact)
- Example: Heat from Sun reaching Earth

## Chapter 8: Water

**Importance of Water**
- Essential for all living things
- Used for drinking, cooking, cleaning
- Needed for agriculture and industry
- Covers about 71% of Earth's surface

**Sources of Water**
**Natural sources**: Rivers, lakes, wells, springs, rain
**Artificial sources**: Dams, reservoirs, water tanks

**Water Cycle**
The continuous movement of water on Earth:
1. **Evaporation**: Sun heats water in oceans, rivers, lakes
2. **Water vapor rises**: Hot water vapor goes up in atmosphere
3. **Condensation**: Water vapor cools and forms clouds
4. **Precipitation**: Water falls as rain, snow, or hail
5. **Collection**: Water flows back to oceans, rivers, underground

**States of Water**
- **Liquid**: Water at normal temperature
- **Solid**: Ice when frozen below 0°C
- **Gas**: Water vapor when heated above 100°C

**Water Pollution**
Contamination of water sources with harmful substances.

**Causes of Water Pollution**
- Industrial waste
- Sewage and garbage
- Chemical fertilizers and pesticides
- Oil spills
- Plastic waste

**Effects of Water Pollution**
- Diseases in humans and animals
- Death of aquatic life
- Contamination of food chain
- Bad smell and taste

**Water Conservation**
Ways to save water:
- Turn off taps when not needed
- Fix leaking pipes and taps
- Reuse water where possible
- Harvest rainwater
- Use water-efficient appliances

## Chapter 9: Air and Atmosphere

**What is Air?**
Air is a mixture of gases that surrounds Earth.
We cannot see air, but we can feel it when it moves (wind).

**Composition of Air**
- **Nitrogen**: 78%
- **Oxygen**: 21%
- **Carbon dioxide**: 0.03%
- **Other gases**: 0.97% (argon, water vapor, etc.)

**Properties of Air**
- Air has mass (weight)
- Air occupies space
- Air exerts pressure
- Air expands when heated
- Air contracts when cooled

**Atmosphere**
The layer of air surrounding Earth is called atmosphere.
It protects us from harmful rays of sun and meteors.

**Layers of Atmosphere**
1. **Troposphere**: Closest to Earth, contains weather
2. **Stratosphere**: Contains ozone layer
3. **Mesosphere**: Meteors burn up here
4. **Thermosphere**: Very hot layer
5. **Exosphere**: Outermost layer

**Importance of Air**
- Essential for breathing (oxygen)
- Supports burning (oxygen)
- Protects from harmful sun rays
- Helps in weather formation
- Sound travels through air

**Air Pollution**
Contamination of air with harmful substances.

**Causes of Air Pollution**
- Vehicle emissions
- Factory smoke
- Burning of fossil fuels
- Construction dust
- Burning garbage

**Effects of Air Pollution**
- Breathing problems
- Acid rain
- Global warming
- Damage to ozone layer
- Smog formation

**How to Reduce Air Pollution**
- Use public transport
- Plant more trees
- Use renewable energy
- Avoid burning garbage
- Use clean fuels

## Chapter 10: Plants

**What are Plants?**
Plants are living things that make their own food using sunlight.
They are very important for life on Earth.

**Parts of a Plant**

**1. Roots**
- Grow underground
- Absorb water and nutrients from soil
- Hold plant firmly in ground
- Store food in some plants

**Types of Roots**
- **Tap root**: One main root with smaller branches (carrot, radish)
- **Fibrous roots**: Many thin roots of similar size (grass, wheat)

**2. Stem**
- Supports the plant
- Transports water and nutrients between roots and leaves
- Holds leaves, flowers, and fruits

**Types of Stems**
- **Woody stems**: Hard and thick (trees)
- **Herbaceous stems**: Soft and green (small plants)

**3. Leaves**
- Make food for the plant through photosynthesis
- Help plant breathe through tiny pores called stomata
- Come in many shapes and sizes

**Parts of a Leaf**
- **Blade**: Flat green part
- **Petiole**: Leaf stalk connecting to stem
- **Veins**: Carry water and food

**4. Flowers**
- Reproductive part of plant
- Attract insects for pollination
- Develop into fruits after fertilization

**Parts of a Flower**
- **Petals**: Colorful parts that attract insects
- **Sepals**: Green parts that protect flower bud
- **Stamen**: Male part (produces pollen)
- **Pistil**: Female part (receives pollen)

**5. Fruits and Seeds**
- Fruits develop from flowers
- Contain seeds inside
- Seeds grow into new plants

**Photosynthesis**
Process by which plants make their own food:
- Plants use sunlight, carbon dioxide, and water
- Chlorophyll (green pigment) captures sunlight
- Produces glucose (food) and oxygen
- Formula: Carbon dioxide + Water + Sunlight → Glucose + Oxygen

**Importance of Plants**
- Provide oxygen for breathing
- Give us food (fruits, vegetables, grains)
- Provide materials (wood, cotton, medicines)
- Make environment beautiful
- Prevent soil erosion
- Reduce air pollution

## Chapter 11: Animals

**Classification of Animals**
Animals can be grouped based on different characteristics:

**Based on Backbone**
- **Vertebrates**: Animals with backbone (fish, birds, mammals, reptiles, amphibians)
- **Invertebrates**: Animals without backbone (insects, worms, jellyfish)

**Based on Food Habits**
- **Herbivores**: Eat only plants (cow, rabbit, deer)
- **Carnivores**: Eat only other animals (lion, tiger, snake)
- **Omnivores**: Eat both plants and animals (humans, bears, pigs)

**Based on Habitat**
- **Terrestrial**: Live on land (elephant, tiger, rabbit)
- **Aquatic**: Live in water (fish, whale, dolphin)
- **Arboreal**: Live on trees (monkey, bird, squirrel)
- **Aerial**: Fly in air (birds, bats, insects)

**Animal Adaptations**
Animals have special features that help them survive in their environment:

**Desert Animals**
- Thick skin to prevent water loss (camel)
- Store water in body (camel's hump)
- Active at night to avoid heat (desert fox)

**Cold Region Animals**
- Thick fur to keep warm (polar bear)
- Layer of fat under skin (penguin)
- Small ears to reduce heat loss (arctic fox)

**Aquatic Animals**
- Streamlined body for swimming (fish)
- Gills to breathe underwater (fish)
- Webbed feet for swimming (duck)

**Life Cycles**
Different animals have different life cycles:

**Butterfly Life Cycle**
1. Egg
2. Larva (caterpillar)
3. Pupa (chrysalis)
4. Adult butterfly

**Frog Life Cycle**
1. Egg
2. Tadpole (lives in water)
3. Young frog (develops legs)
4. Adult frog

**Bird Life Cycle**
1. Egg
2. Chick (baby bird)
3. Young bird
4. Adult bird

## Chapter 12: Human Body

**Body Systems**
Our body has different systems that work together:

**1. Skeletal System**
- Made of bones
- Gives shape and support to body
- Protects internal organs
- Helps in movement
- Adult human has 206 bones

**2. Muscular System**
- Made of muscles
- Helps in movement
- Works with skeletal system
- Heart is also a muscle

**3. Digestive System**
- Breaks down food into nutrients
- Parts: Mouth, stomach, small intestine, large intestine
- Process: Chewing → Swallowing → Digestion → Absorption → Excretion

**4. Respiratory System**
- Helps us breathe
- Takes in oxygen and removes carbon dioxide
- Parts: Nose, windpipe, lungs
- We breathe about 20,000 times a day

**5. Circulatory System**
- Carries blood throughout body
- Heart pumps blood through blood vessels
- Blood carries oxygen and nutrients to all parts
- Heart beats about 100,000 times a day

**6. Nervous System**
- Controls all body functions
- Brain is the control center
- Nerves carry messages between brain and body parts
- Helps us think, feel, and move

**Sense Organs**
We have five main senses:

**1. Eyes (Sight)**
- Help us see
- Can see colors, shapes, movement
- Tears keep eyes clean and moist

**2. Ears (Hearing)**
- Help us hear sounds
- Also help us balance
- Can damage from very loud sounds

**3. Nose (Smell)**
- Helps us smell different odors
- Connected to taste
- Helps us breathe

**4. Tongue (Taste)**
- Helps us taste food
- Can taste sweet, sour, salty, bitter
- Works with nose for full flavor

**5. Skin (Touch)**
- Largest organ of body
- Feels hot, cold, rough, smooth, pressure
- Protects body from germs

**Healthy Habits**
- Eat balanced diet with fruits and vegetables
- Exercise regularly
- Get enough sleep (8-10 hours for children)
- Keep body clean
- Drink plenty of water
- Avoid junk food
- Regular health checkups

## Chapter 13: Our Environment

**What is Environment?**
Everything around us - air, water, land, plants, animals.
We depend on environment for our survival.

**Components of Environment**
**Living components**: Plants, animals, microorganisms
**Non-living components**: Air, water, soil, sunlight, temperature

**Ecosystem**
All living and non-living things in an area working together.
Examples: Forest ecosystem, pond ecosystem, desert ecosystem

**Food Chain**
Shows how energy flows from one living thing to another:
Grass → Rabbit → Fox
(Producer → Primary consumer → Secondary consumer)

**Environmental Problems**

**1. Pollution**
- Air pollution from vehicles and factories
- Water pollution from waste and chemicals
- Soil pollution from pesticides and garbage
- Noise pollution from loud sounds

**2. Deforestation**
- Cutting down forests
- Loss of animal homes
- Increase in carbon dioxide
- Soil erosion

**3. Global Warming**
- Earth getting warmer due to greenhouse gases
- Melting of ice caps
- Rise in sea level
- Climate change

**Conservation**
Protecting our environment for future generations.

**Ways to Conserve Environment**
- Plant more trees
- Use less water and electricity
- Reduce, reuse, recycle waste
- Use public transport
- Avoid using plastic
- Create awareness about environmental issues

**3 R's for Environment**
- **Reduce**: Use less resources
- **Reuse**: Use things again
- **Recycle**: Make new things from old materials

Remember: We have only one Earth. It's our responsibility to take care of it!
            """,
            "social_studies": """
            # SOCIAL STUDIES - Complete Learning Guide

## Chapter 1: Understanding Society

**What is Social Studies?**
Social Studies is the study of people, places, and societies throughout time.
It helps us understand how people live, work, and interact with each other.
It includes history, geography, civics, economics, and culture.

**Why Study Social Studies?**
- Understand our past and how it shapes our present
- Learn about different cultures and places
- Become responsible citizens
- Develop critical thinking skills
- Understand how societies work

**Components of Social Studies**
- **History**: Study of past events and people
- **Geography**: Study of Earth's features and places
- **Civics**: Study of government and citizenship
- **Economics**: Study of how people use resources
- **Culture**: Study of people's way of life

## Chapter 2: Indian History - Ancient Period

**Indus Valley Civilization (2500-1500 BCE)**
One of the world's earliest urban civilizations.

**Key Features:**
- Well-planned cities with grid-pattern streets
- Advanced drainage and water supply systems
- Standardized weights and measures
- No evidence of warfare or weapons
- Trade with other civilizations

**Important Sites:**
- **Harappa**: First site discovered, gave name to civilization
- **Mohenjo-daro**: "Mound of the dead," well-preserved city
- **Dholavira**: Known for water conservation systems
- **Lothal**: Important port city with dockyard

**The Vedic Period (1500-600 BCE)**
Period when Vedas (sacred texts) were composed.

**Early Vedic Period (1500-1000 BCE)**
- Arrival of Aryans in India
- Pastoral and semi-nomadic lifestyle
- Composition of Rig Veda
- Worship of natural forces

**Later Vedic Period (1000-600 BCE)**
- Settlement in Gangetic plains
- Development of agriculture
- Complex social system (varna system)
- Composition of other Vedas and Upanishads

**Rise of New Religions**
**Buddhism (6th century BCE)**
- Founded by Gautama Buddha (Siddhartha)
- Four Noble Truths and Eightfold Path
- Emphasis on non-violence and compassion
- Spread across Asia

**Jainism (6th century BCE)**
- Founded by Mahavira
- Principle of Ahimsa (non-violence)
- Belief in karma and liberation
- Simple living and high thinking

## Chapter 3: Indian History - Medieval Period

**The Mauryan Empire (322-185 BCE)**
First large empire in Indian history.

**Chandragupta Maurya (322-298 BCE)**
- Founded the Mauryan Empire
- Unified most of Indian subcontinent
- Capital at Pataliputra (modern Patna)
- Helped by Chanakya (Kautilya)

**Ashoka the Great (268-232 BCE)**
- Most famous Mauryan ruler
- Initially followed policy of conquest
- After Kalinga War, adopted Buddhism
- Promoted non-violence and moral values
- Built stupas and erected pillars with edicts

**The Gupta Period (320-600 CE)**
Known as the "Golden Age" of Indian history.

**Achievements:**
- Great progress in art, science, and literature
- Decimal system and concept of zero developed
- Great universities like Nalanda and Takshashila
- Famous scholars: Kalidasa, Aryabhatta, Varahamihira
- Religious tolerance and cultural development

**Medieval Invasions**
**Arab Invasions (8th century)**
- Muhammad bin Qasim invaded Sindh (712 CE)
- Introduction of Islam in India
- Cultural exchange between Arabs and Indians

**Turkish Invasions (11th-12th century)**
- Mahmud of Ghazni (971-1030 CE)
- Muhammad Ghori (1149-1206 CE)
- Established Muslim rule in India

**The Delhi Sultanate (1206-1526)**
First Islamic empire in India.

**Major Dynasties:**
- **Slave Dynasty**: Qutub-ud-din Aibak, Iltutmish
- **Khilji Dynasty**: Alauddin Khilji
- **Tughlaq Dynasty**: Muhammad bin Tughlaq
- **Lodi Dynasty**: Ibrahim Lodi

**The Mughal Empire (1526-1857)**
One of the largest empires in Indian history.

**Major Rulers:**
**Babur (1526-1530)**
- Founder of Mughal Empire
- Won First Battle of Panipat (1526)
- Defeated Ibrahim Lodi

**Akbar (1556-1605)**
- Greatest Mughal ruler
- Policy of religious tolerance (Din-i-Ilahi)
- Administrative reforms
- Cultural synthesis

**Shah Jahan (1628-1658)**
- Built Taj Mahal in memory of wife Mumtaz
- Period of architectural excellence
- Built Red Fort and Jama Masjid

**Aurangzeb (1658-1707)**
- Last great Mughal emperor
- Religious conservative
- Expanded empire to maximum extent
- Empire declined after his death

## Chapter 4: Indian Freedom Struggle

**British Rule in India**
**East India Company (1600-1858)**
- Initially came for trade
- Gradually established political control
- Battle of Plassey (1757) - turning point
- Exploited India's resources

**Revolt of 1857**
First major uprising against British rule.
- Also called First War of Independence
- Started from Meerut, spread across North India
- Led by Bahadur Shah Zafar, Rani Lakshmibai, Tatya Tope
- Suppressed by British, but awakened national consciousness

**Rise of Nationalism**
**Indian National Congress (1885)**
- First national political organization
- Founded by A.O. Hume
- Early leaders: Dadabhai Naoroji, Surendranath Banerjee

**Muslim League (1906)**
- Formed to protect Muslim interests
- Later demanded separate nation for Muslims

**Freedom Fighters and Movements**

**Mahatma Gandhi (1869-1948)**
- Father of the Nation
- Philosophy of Satyagraha (non-violent resistance)
- Led major movements:
  - Non-Cooperation Movement (1920-22)
  - Salt March/Dandi March (1930)
  - Quit India Movement (1942)

**Other Great Leaders:**
- **Jawaharlal Nehru**: First Prime Minister
- **Sardar Vallabhbhai Patel**: Iron Man of India
- **Subhas Chandra Bose**: Netaji, formed Indian National Army
- **Bhagat Singh**: Revolutionary freedom fighter
- **Rani Lakshmibai**: Queen of Jhansi, fought against British

**Independence and Partition (1947)**
- India gained independence on August 15, 1947
- Partition into India and Pakistan
- Massive migration and communal violence
- Jawaharlal Nehru became first Prime Minister

## Chapter 5: Indian Geography

**Location and Boundaries**
- India is located in South Asia
- Lies between 8°4'N to 37°6'N latitude
- Lies between 68°7'E to 97°25'E longitude
- Bordered by Pakistan, China, Nepal, Bhutan, Bangladesh, Myanmar
- Surrounded by Arabian Sea, Bay of Bengal, Indian Ocean

**Physical Features**

**The Himalayas**
- World's highest mountain range
- Formed due to collision of Indian and Eurasian plates
- Three parallel ranges:
  - Greater Himalayas (Himadri)
  - Lesser Himalayas (Himachal)
  - Outer Himalayas (Shiwaliks)
- Highest peak: Mount Everest (8,849 m)

**The Northern Plains**
- Formed by rivers Ganges, Brahmaputra, and Indus
- Very fertile due to alluvial soil
- Most densely populated region
- Agriculture is main occupation

**The Peninsular Plateau**
- Oldest part of Indian landmass
- Rich in minerals
- Divided by rivers Narmada and Tapti
- Important cities: Bangalore, Hyderabad, Chennai

**The Coastal Plains**
- **Western Coastal Plain**: Narrow, between Western Ghats and Arabian Sea
- **Eastern Coastal Plain**: Broader, between Eastern Ghats and Bay of Bengal
- Important for fishing and trade

**The Islands**
- **Lakshadweep**: In Arabian Sea, coral islands
- **Andaman and Nicobar**: In Bay of Bengal, volcanic islands

**Rivers of India**

**The Ganges System**
- **Ganges**: Most sacred river, flows through North India
- **Yamuna**: Tributary of Ganges, flows through Delhi
- **Brahmaputra**: Flows through Assam, forms delta with Ganges

**The Indus System**
- Flows mainly through Pakistan
- Important tributaries: Jhelum, Chenab, Ravi, Beas, Sutlej

**Peninsular Rivers**
- **Narmada**: Flows westward into Arabian Sea
- **Tapti**: Flows westward into Arabian Sea
- **Godavari**: Largest peninsular river
- **Krishna**: Important river of South India
- **Kaveri**: Sacred river of Tamil Nadu

**Climate of India**
India has tropical monsoon climate.

**Seasons:**
- **Winter (December-February)**: Cool and dry
- **Summer (March-May)**: Hot and dry
- **Monsoon (June-September)**: Rainy season
- **Post-monsoon (October-November)**: Retreating monsoon

**Monsoons:**
- **Southwest Monsoon**: Brings most of India's rainfall
- **Northeast Monsoon**: Affects mainly Tamil Nadu

## Chapter 6: Indian Government and Civics

**Democracy**
Government by the people, for the people, of the people.

**Features of Democracy:**
- People elect their representatives
- Rule of law
- Individual rights and freedoms
- Regular elections
- Accountability of government

**Indian Constitution**
Supreme law of India, adopted on January 26, 1950.

**Preamble**
Introduction to the Constitution, states the goals and values.
"We, the people of India, having solemnly resolved to constitute India into a SOVEREIGN SOCIALIST SECULAR DEMOCRATIC REPUBLIC..."

**Key Words:**
- **Sovereign**: India is free to make its own decisions
- **Socialist**: Equality and welfare for all
- **Secular**: Equal respect for all religions
- **Democratic**: Government by the people
- **Republic**: Head of state is elected, not hereditary

**Fundamental Rights**
Basic rights guaranteed to all citizens.

**Six Fundamental Rights:**
1. **Right to Equality**: Equal treatment before law
2. **Right to Freedom**: Freedom of speech, expression, movement
3. **Right against Exploitation**: Protection from forced labor
4. **Right to Freedom of Religion**: Freedom to practice any religion
5. **Cultural and Educational Rights**: Protection of minority cultures
6. **Right to Constitutional Remedies**: Right to approach courts

**Fundamental Duties**
Responsibilities of citizens toward the nation.

**Important Duties:**
- Respect the Constitution and national symbols
- Defend the country
- Promote harmony among all people
- Protect environment and wildlife
- Develop scientific temper
- Safeguard public property

**Structure of Government**

**Central Government**
**Executive Branch:**
- **President**: Head of State, elected for 5 years
- **Prime Minister**: Head of Government, leader of majority party
- **Council of Ministers**: Helps Prime Minister in administration

**Legislative Branch:**
- **Parliament**: Makes laws for the country
- **Lok Sabha**: Lower house, directly elected by people
- **Rajya Sabha**: Upper house, represents states

**Judicial Branch:**
- **Supreme Court**: Highest court, guardian of Constitution
- **High Courts**: Highest courts in states
- **District Courts**: Lower courts in districts

**State Government**
- **Governor**: Constitutional head of state
- **Chief Minister**: Head of state government
- **State Legislature**: Makes laws for the state
- **State High Court**: Highest court in the state

**Local Government**
**Rural Areas:**
- **Gram Panchayat**: Village level
- **Panchayat Samiti**: Block level
- **Zilla Panchayat**: District level

**Urban Areas:**
- **Municipal Corporation**: Large cities
- **Municipal Council**: Smaller cities
- **Nagar Panchayat**: Towns

## Chapter 7: Rights and Duties of Citizens

**Who is a Citizen?**
A citizen is a legal member of a country who enjoys certain rights and has certain duties.

**Ways to Become Indian Citizen:**
- **By birth**: Born in India
- **By descent**: Parents are Indian citizens
- **By registration**: Married to Indian citizen
- **By naturalization**: Living in India for specified period

**Rights of Citizens**
Already covered under Fundamental Rights.

**Additional Rights:**
- Right to vote (18 years and above)
- Right to contest elections
- Right to information
- Right to education
- Right to work

**Duties of Citizens**

**Constitutional Duties:**
- Follow the Constitution
- Respect national symbols (flag, anthem)
- Protect sovereignty and integrity of India
- Defend the country when needed
- Promote harmony among all people
- Preserve rich heritage and culture
- Protect environment
- Develop scientific attitude
- Safeguard public property
- Strive for excellence

**Social Duties:**
- Pay taxes honestly
- Vote in elections
- Help maintain law and order
- Respect rights of others
- Participate in community activities
- Keep public places clean

**Rights of Children**
Children have special rights because they need protection.

**Important Rights:**
- Right to name and nationality
- Right to education
- Right to healthcare
- Right to protection from abuse
- Right to express opinions
- Right to play and recreation
- Right to protection from child labor

**Child Protection Laws:**
- **Right to Education Act**: Free and compulsory education till 14 years
- **Child Labor Act**: Prohibits employment of children below 14
- **POCSO Act**: Protection from sexual offenses

## Chapter 8: Culture and Heritage

**Unity in Diversity**
India's strength lies in its diversity.

**Diversity in India:**
- **Languages**: 22 official languages, hundreds of dialects
- **Religions**: Hinduism, Islam, Christianity, Sikhism, Buddhism, Jainism
- **Festivals**: Different festivals across regions
- **Food**: Varied cuisines across states
- **Clothing**: Different traditional dresses
- **Art and Crafts**: Various art forms and handicrafts

**Common Elements:**
- Respect for elders
- Joint family system
- Hospitality to guests
- Love for music and dance
- Spiritual values

**Major Festivals**

**National Festivals:**
- **Independence Day (August 15)**: Celebrates freedom from British rule
- **Republic Day (January 26)**: Celebrates adoption of Constitution
- **Gandhi Jayanti (October 2)**: Birthday of Mahatma Gandhi

**Religious Festivals:**
- **Diwali**: Festival of lights (Hindu)
- **Eid**: Celebrates end of Ramadan (Muslim)
- **Christmas**: Birth of Jesus Christ (Christian)
- **Dussehra**: Victory of good over evil (Hindu)
- **Holi**: Festival of colors (Hindu)
- **Gurpurab**: Birthday of Sikh Gurus (Sikh)

**Regional Festivals:**
- **Onam**: Harvest festival of Kerala
- **Pongal**: Harvest festival of Tamil Nadu
- **Baisakhi**: Harvest festival of Punjab
- **Durga Puja**: Important festival of West Bengal

**Art and Culture**

**Classical Dances:**
- **Bharatanatyam**: Tamil Nadu
- **Kathak**: North India
- **Odissi**: Odisha
- **Kuchipudi**: Andhra Pradesh
- **Kathakali**: Kerala
- **Manipuri**: Manipur
- **Mohiniyattam**: Kerala
- **Sattriya**: Assam

**Musical Traditions:**
- **Hindustani Music**: North Indian classical music
- **Carnatic Music**: South Indian classical music
- **Folk Music**: Regional traditional music

**UNESCO World Heritage Sites in India:**
- Taj Mahal (Uttar Pradesh)
- Red Fort (Delhi)
- Qutub Minar (Delhi)
- Ajanta and Ellora Caves (Maharashtra)
- Khajuraho Temples (Madhya Pradesh)
- Hampi (Karnataka)
- Fatehpur Sikri (Uttar Pradesh)
- Sun Temple, Konark (Odisha)

## Chapter 9: Economic Life

**What is Economics?**
Study of how people produce, distribute, and use goods and services.

**Basic Economic Concepts**

**Needs and Wants**
- **Needs**: Essential things for survival (food, water, shelter, clothing)
- **Wants**: Things we desire but can live without (toys, entertainment)

**Goods and Services**
- **Goods**: Physical items we can touch (food, clothes, books)
- **Services**: Actions done for others (teaching, medical care, transportation)

**Primary, Secondary, Tertiary Activities**

**Primary Activities**
- Extract natural resources from earth
- Examples: Farming, fishing, mining, forestry
- Provide raw materials for other industries

**Secondary Activities**
- Transform raw materials into finished products
- Examples: Manufacturing, construction, food processing
- Create goods that people need and want

**Tertiary Activities**
- Provide services to people
- Examples: Education, healthcare, banking, transportation
- Support other economic activities

**Agriculture in India**
Most important occupation in India.

**Types of Farming:**
- **Subsistence Farming**: Growing crops for own family's needs
- **Commercial Farming**: Growing crops to sell in market

**Major Crops:**
- **Food Crops**: Rice, wheat, jowar, bajra, maize
- **Cash Crops**: Cotton, sugarcane, jute, tea, coffee
- **Spices**: Pepper, cardamom, turmeric, chili

**Seasons:**
- **Kharif**: Summer crops (rice, cotton, sugarcane)
- **Rabi**: Winter crops (wheat, barley, peas)
- **Zaid**: Summer crops grown with irrigation

**Industries in India**

**Types of Industries:**
- **Large Scale**: Big factories with many workers
- **Small Scale**: Small workshops and factories
- **Cottage Industries**: Home-based production

**Major Industries:**
- **Textile Industry**: Cotton, silk, synthetic fabrics
- **Iron and Steel**: Basic industry for development
- **Information Technology**: Software and services
- **Automobile**: Cars, motorcycles, commercial vehicles

**Transportation**
Movement of people and goods from one place to another.

**Means of Transport:**
- **Land Transport**: Roads, railways
- **Water Transport**: Ships, boats
- **Air Transport**: Aeroplanes, helicopters

**Communication**
Sharing information and ideas.

**Means of Communication:**
- **Personal Communication**: Letters, telephone, email
- **Mass Communication**: Newspapers, radio, television, internet

## Chapter 10: Global Citizenship

**What is Global Citizenship?**
Understanding that we are part of a larger world community and have responsibilities toward all people and the planet.

**Qualities of Global Citizens:**
- Respect for diversity
- Concern for environment
- Understanding of global issues
- Willingness to help others
- Open-minded thinking

**United Nations (UN)**
International organization working for world peace and cooperation.

**Purposes of UN:**
- Maintain international peace and security
- Develop friendly relations among nations
- Solve international problems
- Promote human rights

**Environmental Issues**
Problems affecting our planet.

**Major Issues:**
- **Climate Change**: Global warming due to greenhouse gases
- **Pollution**: Air, water, and soil contamination
- **Deforestation**: Cutting down forests
- **Loss of Biodiversity**: Extinction of plants and animals

**Solutions:**
- Use renewable energy
- Reduce, reuse, recycle
- Plant more trees
- Use public transport
- Conserve water and electricity

**Sustainable Development**
Meeting present needs without compromising future generations.

**Goals:**
- End poverty
- Ensure quality education
- Promote gender equality
- Ensure clean water and sanitation
- Take action on climate change
- Protect life on land and in water

Remember: Social Studies helps us understand our place in the world and how we can contribute to making it a better place for everyone!
            """,
            "english": """
            # ENGLISH LANGUAGE AND LITERATURE - Complete Learning Guide

## Chapter 1: English Grammar Fundamentals

**Parts of Speech**
Every word in English belongs to one of eight categories:

**1. Nouns**
Words that name people, places, things, or ideas.
- **Common nouns**: General names (boy, city, book)
- **Proper nouns**: Specific names (Ram, Delhi, Ramayana)
- **Collective nouns**: Groups (team, family, flock)
- **Abstract nouns**: Ideas or feelings (love, happiness, courage)

**2. Pronouns**
Words that replace nouns to avoid repetition.
- **Personal**: I, you, he, she, it, we, they
- **Possessive**: mine, yours, his, hers, ours, theirs
- **Demonstrative**: this, that, these, those
- **Interrogative**: who, what, which, whose

**3. Verbs**
Words that show action or state of being.
- **Action verbs**: run, write, sing, dance
- **Linking verbs**: is, am, are, was, were, become, seem
- **Helping verbs**: have, has, had, will, would, should, could

**4. Adjectives**
Words that describe or modify nouns.
- **Descriptive**: beautiful, tall, smart, red
- **Quantitative**: some, many, few, several
- **Demonstrative**: this, that, these, those
- **Possessive**: my, your, his, her, their

**5. Adverbs**
Words that modify verbs, adjectives, or other adverbs.
- **Manner**: quickly, carefully, beautifully
- **Time**: now, yesterday, soon, always
- **Place**: here, there, everywhere, outside
- **Degree**: very, quite, extremely, rather

**6. Prepositions**
Words that show relationships between other words.
Examples: in, on, at, by, with, from, to, under, over, between

**7. Conjunctions**
Words that join words, phrases, or clauses.
- **Coordinating**: and, but, or, nor, for, so, yet
- **Subordinating**: because, since, if, when, while, although

**8. Interjections**
Words that express sudden emotion.
Examples: Oh! Wow! Hurray! Alas! Ouch!

## Chapter 2: Sentence Structure

**What is a Sentence?**
A complete sentence expresses a complete thought and has two main parts:
- **Subject**: Who or what the sentence is about
- **Predicate**: What the subject does or is

**Types of Sentences by Purpose**

**1. Declarative Sentences**
Make statements or give information.
Examples: 
- The sun rises in the east.
- I like to read books.

**2. Interrogative Sentences**
Ask questions.
Examples:
- What is your name?
- Where are you going?

**3. Imperative Sentences**
Give commands or make requests.
Examples:
- Please close the door.
- Study hard for your exams.

**4. Exclamatory Sentences**
Express strong emotion.
Examples:
- What a beautiful day it is!
- How talented she is!

**Types of Sentences by Structure**

**1. Simple Sentences**
Have one independent clause (subject + predicate).
Examples:
- Birds fly.
- The children played in the park.

**2. Compound Sentences**
Have two or more independent clauses joined by conjunctions.
Examples:
- I wanted to go, but it was raining.
- She studied hard, so she passed the exam.

**3. Complex Sentences**
Have one independent clause and one or more dependent clauses.
Examples:
- When I arrived, the meeting had already started.
- The book that you gave me is very interesting.

## Chapter 3: Tenses

**Present Tense**
Shows actions happening now or general truths.

**Simple Present**
- Form: Subject + base verb (+ s/es for he/she/it)
- Examples: I play cricket. She reads books. The sun rises in the east.

**Present Continuous**
- Form: Subject + am/is/are + verb + ing
- Examples: I am reading. They are playing. He is writing a letter.

**Present Perfect**
- Form: Subject + have/has + past participle
- Examples: I have finished my work. She has eaten lunch.

**Past Tense**
Shows actions that happened before now.

**Simple Past**
- Form: Subject + past form of verb
- Examples: I played cricket yesterday. She read the book last week.

**Past Continuous**
- Form: Subject + was/were + verb + ing
- Examples: I was reading when you called. They were playing in the garden.

**Past Perfect**
- Form: Subject + had + past participle
- Examples: I had finished my homework before dinner. She had left when I arrived.

**Future Tense**
Shows actions that will happen later.

**Simple Future**
- Form: Subject + will + base verb
- Examples: I will go to school tomorrow. She will help you.

**Future Continuous**
- Form: Subject + will be + verb + ing
- Examples: I will be studying at 8 PM. They will be traveling next week.

**Future Perfect**
- Form: Subject + will have + past participle
- Examples: I will have completed the project by Monday.

## Chapter 4: Punctuation

**Period (.)**
- Ends declarative and imperative sentences
- Used in abbreviations (Dr., Mr., etc.)

**Question Mark (?)**
- Ends interrogative sentences
- Example: What time is it?

**Exclamation Mark (!)**
- Shows strong emotion or surprise
- Example: What a wonderful surprise!

**Comma (,)**
- Separates items in a series
- Sets off introductory words or phrases  
- Separates independent clauses before conjunctions
- Examples: I bought apples, oranges, and bananas. When I arrived, everyone was waiting.

**Apostrophe (')**
- Shows possession: Ram's book, children's toys
- Forms contractions: don't, can't, it's, we're

**Quotation Marks (" ")**
- Enclose direct speech: She said, "I am happy."
- Mark titles of short works: "The Last Leaf" is a famous story.

**Colon (:)**
- Introduces a list or explanation
- Example: You need these items: pen, paper, and eraser.

**Semicolon (;)**
- Joins closely related independent clauses
- Example: I love reading; books are my best friends.

## Chapter 5: Vocabulary Building

**Root Words**
Base words that can stand alone and have meaning.
Examples: play, write, happy, kind

**Prefixes**
Word parts added to the beginning of root words.
- **un-**: unhappy, unfair, unable
- **re-**: rewrite, return, replay  
- **pre-**: preview, prepare, prevent
- **dis-**: disagree, dislike, disappear
- **mis-**: mistake, misplace, misunderstand

**Suffixes**
Word parts added to the end of root words.
- **-ly**: quickly, slowly, carefully
- **-ful**: helpful, beautiful, colorful
- **-less**: hopeless, careless, harmless
- **-er/-or**: teacher, writer, actor
- **-tion/-sion**: education, discussion, creation

**Synonyms**
Words with similar meanings.
Examples:
- Happy: glad, joyful, cheerful, delighted
- Big: large, huge, enormous, giant
- Small: tiny, little, miniature, petite

**Antonyms**
Words with opposite meanings.
Examples:
- Hot ↔ Cold
- Happy ↔ Sad  
- Fast ↔ Slow
- Light ↔ Dark

**Homophones**
Words that sound the same but have different meanings and spellings.
Examples:
- There, their, they're
- To, too, two
- Write, right, rite
- Hear, here

## Chapter 6: Reading Comprehension

**Reading Strategies**

**Before Reading**
- Preview the text (title, headings, pictures)
- Make predictions about the content
- Set a purpose for reading

**During Reading**
- Read actively and think about what you're reading
- Ask questions about the text
- Make connections to your own experiences
- Visualize what you're reading
- Take notes of important points

**After Reading**
- Summarize what you read
- Think about the main message
- Discuss with others
- Apply what you learned

**Finding Main Ideas**
The main idea is the most important point the author wants to make.
- Often found in the first or last sentence of a paragraph
- Supporting details give more information about the main idea
- Ask yourself: "What is this mostly about?"

**Making Inferences**
Using clues from the text plus your own knowledge to figure out something not directly stated.
- Look for hints and clues in the text
- Think about what you already know
- Make logical conclusions

**Understanding Context Clues**
Use surrounding words to figure out unfamiliar words.
- **Definition clues**: The word is defined in the sentence
- **Example clues**: Examples help explain the word
- **Contrast clues**: Opposite words give hints
- **General context**: Overall meaning of the passage helps

## Chapter 7: Writing Skills

**The Writing Process**

**1. Prewriting**
- Choose your topic
- Think about your audience
- Brainstorm ideas
- Organize your thoughts
- Make an outline

**2. Drafting**
- Write your first version
- Don't worry about perfection
- Focus on getting your ideas down
- Follow your outline

**3. Revising**
- Read your draft
- Check if ideas are clear and well-organized
- Add, remove, or rearrange content
- Make sure it makes sense

**4. Editing**
- Check spelling, grammar, and punctuation
- Fix sentence structure problems
- Make sure capitalization is correct
- Proofread carefully

**5. Publishing**
- Create your final copy
- Share with your intended audience

**Types of Writing**

**Narrative Writing**
Tells a story with characters, setting, and plot.
- Has a beginning, middle, and end
- Uses descriptive language
- Often written in first person (I, me) or third person (he, she, they)

**Descriptive Writing**
Uses sensory details to paint a picture with words.
- Appeals to the five senses (sight, sound, smell, taste, touch)
- Uses specific adjectives and adverbs
- Helps readers visualize what you're describing

**Expository Writing**
Explains or informs about a topic.
- Uses facts and examples
- Has clear organization
- Common types: how-to, compare/contrast, cause and effect

**Persuasive Writing**
Tries to convince readers to agree with your opinion.
- States your position clearly
- Gives reasons and evidence
- Addresses opposing viewpoints
- Uses persuasive language

## Chapter 8: Poetry

**What is Poetry?**
Poetry is a form of literature that uses rhythm, rhyme, and imagery to express emotions and ideas.

**Elements of Poetry**

**Rhyme**
Words that end with similar sounds.
- **End rhyme**: Rhymes at the end of lines
- **Internal rhyme**: Rhymes within a line
- **Rhyme scheme**: Pattern of rhymes (ABAB, AABB)

**Rhythm**
The beat or pattern of stressed and unstressed syllables.
Creates musicality in poems.

**Imagery**
Vivid descriptions that appeal to the senses.
Helps readers create mental pictures.

**Metaphor**
Direct comparison between two unlike things.
Example: "Life is a journey."

**Simile**
Comparison using "like" or "as."
Example: "She sings like a bird."

**Personification**
Giving human qualities to non-human things.
Example: "The wind whispered through the trees."

**Alliteration**
Repetition of beginning consonant sounds.
Example: "Peter Piper picked a peck of pickled peppers."

**Types of Poems**

**Haiku**
Traditional Japanese poem with 3 lines:
- First line: 5 syllables
- Second line: 7 syllables  
- Third line: 5 syllables

**Limerick**
Funny 5-line poem with AABBA rhyme scheme.
Lines 1, 2, and 5 rhyme and are longer.
Lines 3 and 4 rhyme and are shorter.

**Free Verse**
Poetry without regular rhyme or rhythm pattern.
Focuses on imagery and emotion rather than structure.

## Chapter 9: Literature

**Elements of Stories**

**Characters**
People, animals, or beings in a story.
- **Main character (protagonist)**: Most important character
- **Supporting characters**: Help tell the story
- **Antagonist**: Character who opposes the main character

**Setting**
When and where the story takes place.
- **Time**: Past, present, future, specific time period
- **Place**: Geographic location, specific building, etc.

**Plot**
Sequence of events in a story.
- **Exposition**: Introduction of characters and setting
- **Rising action**: Events leading to the climax
- **Climax**: Most exciting or turning point
- **Falling action**: Events after the climax
- **Resolution**: How the story ends

**Theme**
The main message or lesson of the story.
What the author wants readers to learn or understand.

**Point of View**
Who tells the story.
- **First person**: Narrator is part of the story (I, me, we)
- **Third person**: Narrator is outside the story (he, she, they)
- **Third person omniscient**: Narrator knows thoughts of all characters

**Conflict**
The main problem or struggle in the story.
- **Person vs. person**: Character against another character
- **Person vs. nature**: Character against natural forces
- **Person vs. self**: Character's internal struggle
- **Person vs. society**: Character against social norms

## Chapter 10: Speaking and Listening

**Effective Speaking**

**Preparation**
- Know your topic well
- Organize your thoughts
- Practice what you want to say
- Think about your audience

**Delivery**
- Speak clearly and loudly enough
- Make eye contact with your audience
- Use gestures and facial expressions
- Stand or sit up straight
- Speak at appropriate pace (not too fast or slow)

**Types of Speaking**

**Conversation**
Informal talking with others.
- Take turns speaking and listening
- Ask questions to show interest
- Stay on topic
- Be respectful of others' opinions

**Presentations**
Formal speaking to inform or persuade.
- Have clear introduction, body, and conclusion
- Use visual aids if helpful
- Practice beforehand
- Be prepared for questions

**Storytelling**
Sharing stories in engaging way.
- Use descriptive language
- Vary your voice for different characters
- Include gestures and expressions
- Have clear beginning, middle, and end

**Active Listening**

**What is Active Listening?**
Paying full attention to what someone is saying and showing that you understand.

**How to Be an Active Listener**
- Look at the speaker
- Don't interrupt
- Ask questions for clarification
- Nod to show you're following
- Summarize what you heard
- Avoid distractions (phones, other conversations)

**Benefits of Good Listening**
- Learn new information
- Show respect for others
- Build better relationships
- Avoid misunderstandings
- Become a better communicator

## Chapter 11: Study Skills

**Note-Taking**
- Write down key points, not everything
- Use abbreviations and symbols
- Organize notes with headings and bullet points
- Review and rewrite notes after class
- Use different colors for different topics

**Reading Strategies**
- Skim before reading to get overview
- Set purpose for reading
- Take breaks when needed
- Ask questions while reading
- Summarize after reading

**Test Preparation**
- Start studying early, don't wait until last minute
- Break study sessions into manageable chunks
- Review notes regularly
- Practice with sample questions
- Get enough sleep before tests
- Stay calm and confident

**Time Management**
- Make a study schedule
- Set priorities
- Avoid procrastination
- Take regular breaks
- Balance study time with recreational activities

## Chapter 12: Creative Writing

**Getting Ideas**
- Observe the world around you
- Keep a journal of interesting thoughts
- Ask "What if?" questions
- Use your own experiences
- Read lots of different books
- Talk to interesting people

**Writing Stories**

**Creating Characters**
- Give characters distinct personalities
- Think about their goals and motivations
- Consider their backgrounds and experiences
- Make them face challenges and grow

**Building Plot**
- Start with an interesting situation
- Create obstacles for your characters
- Build tension gradually
- Include unexpected twists
- Provide satisfying resolution

**Setting Description**
- Use all five senses
- Show, don't just tell
- Make setting affect the mood
- Research if writing about unfamiliar places

**Dialogue**
- Make it sound natural
- Give each character a unique voice
- Use dialogue to reveal character and advance plot
- Don't forget dialogue tags ("he said," "she asked")

**Editing Your Work**
- Let your writing "rest" before editing
- Read aloud to catch problems
- Check for clarity and flow
- Fix grammar and spelling errors
- Ask others to read and give feedback

Remember: Writing is a skill that improves with practice. The more you read and write, the better you'll become!
            """,
        }

        return fallback_contents.get(
            subject, f"Basic content for {subject} will be available soon."
        )

    def create_fallback_institutional_content(self) -> str:
        """Create fallback institutional content"""
        return """
    # INSTITUTIONAL FAQS - Complete Information Guide

    ## Chapter 1: Admission Information

    **Admission Process and Requirements**

    **When to Apply**
    Admission applications are typically available from March to May each year.
    Online applications can be submitted through the school website.
    Offline applications are available at the school office during working hours.
    Early applications are encouraged as seats are limited.

    **Required Documents**
    For new admissions, please bring the following documents:
    - Birth certificate (original and photocopy)
    - Previous school transfer certificate
    - Previous year's mark sheet or progress report
    - Address proof (electricity bill, ration card, or Aadhar card)
    - Passport-size photographs (4 copies)
    - Medical certificate from registered doctor
    - Caste certificate (if applicable for reservation)
    - Income certificate (for fee concession applications)

    **Age Criteria**
    Age requirements as on March 31st of the admission year:
    - Nursery: 3 years completed
    - LKG: 4 years completed
    - UKG: 5 years completed
    - Class 1: 6 years completed
    - Class 6: 11 years completed
    - Class 9: 14 years completed
    - Class 11: 16 years completed

    **Admission Test and Interview**
    For classes 1 to 8: Simple interaction to assess readiness
    For classes 9 and 11: Written test covering previous class syllabus
    For all classes: Parent-child interview to understand expectations
    Test dates are announced on school website and notice board

    **Merit List and Selection**
    Merit list is prepared based on:
    - Academic performance in previous class
    - Entrance test performance (if applicable)
    - Interview assessment
    - Availability of seats in respective sections
    - Reservation policy as per government guidelines

    **Admission Confirmation**
    Selected candidates must:
    - Report to school within 7 days of selection
    - Pay admission fee and first term fees
    - Submit all original documents for verification
    - Complete medical examination by school doctor
    - Purchase books and uniforms from authorized vendors

    ## Chapter 2: Fee Structure and Payment

    **Annual Fee Components**
    The annual fee structure includes:
    - Tuition fees (academic instruction)
    - Development fees (infrastructure maintenance)
    - Examination fees (internal and board exams)
    - Activity fees (sports, cultural, extracurricular)
    - Library fees (books, magazines, digital resources)
    - Laboratory fees (science practicals, computer lab)
    - Transport fees (optional, route-wise charges)

    **Payment Options and Schedule**
    Fees can be paid in following modes:
    - **Quarterly**: Four installments (April, July, October, January)
    - **Half-yearly**: Two installments (April, October)
    - **Annually**: Single payment (April) with 5% discount

    **Payment Methods**
    - Online payment through school website (net banking, credit/debit cards, UPI)
    - Bank challan at authorized branches
    - Demand draft in favor of school
    - Cash payment at school office (only for amounts below ₹20,000)

    **Late Payment Policy**
    - Late fee of ₹100 for payments made after due date
    - After 30 days delay: ₹500 late fee + interest at 2% per month
    - After 60 days delay: Student's name may be struck off from rolls
    - No late fee for payments delayed due to bank holidays or natural calamities

    **Fee Concessions and Scholarships**
    **Government Scholarships:**
    - SC/ST students: 100% fee waiver for annual income below ₹2.5 lakhs
    - OBC students: 50% fee concession for annual income below ₹1 lakh
    - Minority scholarships available for eligible communities

    **Merit Scholarships:**
    - 100% scholarship for students scoring above 95% in board exams
    - 50% scholarship for students scoring above 90% in board exams
    - Sports scholarship for state and national level players

    **Need-based Assistance:**
    - Financial aid for economically weaker sections
    - Installment facility for emergency situations
    - Work-study programs for senior students

    **Refund Policy**
    - Full refund if withdrawal before start of academic session
    - 75% refund if withdrawal within first month
    - 50% refund if withdrawal within first quarter
    - No refund after first quarter except for medical reasons
    - Caution money refunded after clearance from all departments

    ## Chapter 3: Academic Calendar and Schedule

    **Academic Year Structure**
    The academic year runs from April to March with following pattern:
    - **First Term**: April to September (followed by Diwali vacation)
    - **Second Term**: November to March (includes winter and summer breaks)
    - Working days: Minimum 220 days as per education board guidelines

    **Daily Schedule**
    **Primary Classes (1-5):**
    - Assembly: 8:00 AM - 8:20 AM
    - Classes: 8:20 AM - 2:30 PM
    - Lunch break: 12:30 PM - 1:10 PM
    - Activities: 2:30 PM - 3:30 PM (optional)

    **Secondary Classes (6-10):**
    - Assembly: 8:00 AM - 8:20 AM
    - Classes: 8:20 AM - 3:00 PM
    - Lunch break: 1:00 PM - 1:40 PM
    - Extra classes: 3:00 PM - 4:00 PM (optional)

    **Senior Secondary (11-12):**
    - Classes: 8:00 AM - 3:30 PM
    - Break: 11:00 AM - 11:20 AM
    - Lunch: 1:30 PM - 2:10 PM
    - Practical sessions: 3:30 PM - 5:30 PM

    **Holiday Calendar**
    **National Holidays:**
    - Independence Day (August 15)
    - Republic Day (January 26)
    - Gandhi Jayanti (October 2)

    **Religious Festivals:**
    - Diwali vacation (5 days)
    - Dussehra (1 day)
    - Eid (1 day)
    - Christmas (1 day)
    - Holi (1 day)

    **Seasonal Breaks:**
    - Summer vacation: May-June (45 days)
    - Winter break: Last week of December (10 days)
    - Monsoon break: August (if required, 2-3 days)

    **Parent-Teacher Meetings**
    - Monthly meetings on first Saturday of each month
    - Special meetings before exams for classes 10 and 12
    - Individual consultations available on appointment
    - WhatsApp group updates for urgent communications

    **Important Events Calendar**
    - **April**: New session begins, orientation programs
    - **May**: Summer camp activities
    - **July**: Inter-house competitions begin
    - **August**: Independence Day celebrations, teacher training
    - **September**: First term exams
    - **October**: Dussehra celebrations, science exhibition
    - **November**: Annual sports day
    - **December**: Winter carnival, Christmas celebrations
    - **January**: Republic Day parade, annual day preparations
    - **February**: Annual day celebrations, board exam preparation
    - **March**: Final exams, farewell programs

    ## Chapter 4: Examination System and Assessment

    **Assessment Pattern**
    The school follows Continuous Comprehensive Evaluation (CCE) system:
    - **Formative Assessment (40%)**: Ongoing evaluation throughout year
    - **Summative Assessment (60%)**: Term-end examinations

    **Formative Assessment Components**
    - Class work and participation (10%)
    - Homework and assignments (10%)
    - Projects and presentations (10%)
    - Periodic tests and quizzes (10%)

    **Summative Assessment Components**
    - First term examination (30%)
    - Second term examination (30%)

    **Examination Schedule**
    **Periodic Tests:**
    - Monthly unit tests for all subjects
    - Surprise tests to ensure regular study
    - Open book tests for application-based subjects

    **Term Examinations:**
    - Half-yearly exams: September-October
    - Annual exams: February-March
    - Practical exams: Before theory papers
    - Board exams (10th and 12th): As per board schedule

    **Grading System**
    **For Classes 1-8:**
    - A+: 91-100% (Outstanding)
    - A: 81-90% (Excellent)
    - B+: 71-80% (Very Good)
    - B: 61-70% (Good)
    - C+: 51-60% (Satisfactory)
    - C: 41-50% (Acceptable)
    - D: 33-40% (Needs Improvement)
    - E: Below 33% (Unsatisfactory)

    **For Classes 9-12:**
    - Percentage marking system as per board guidelines
    - Grace marks as per board rules
    - Improvement exam facility available

    **Result Declaration**
    - Unit test results: Within one week
    - Term examination results: Within 15 days
    - Board results: As per board announcement
    - Results available on school website and parent app

    **Re-examination Policy**
    - Available for students who miss exams due to medical reasons
    - Medical certificate from registered practitioner required
    - Re-exam fee as per school rules
    - Generally conducted within 15 days of original exam

    **Progress Reports**
    - Monthly progress cards for classes 1-8
    - Term-wise report cards for classes 9-12
    - Parent signature required on all progress reports
    - Detention letters sent for consistent poor performance

    ## Chapter 5: Curriculum and Syllabus

    **Curriculum Framework**
    The school follows [Board Name] curriculum designed to:
    - Develop conceptual understanding
    - Encourage critical thinking and creativity
    - Promote holistic development
    - Prepare students for competitive exams
    - Foster global citizenship values

    **Board Affiliation**
    - Primary Section: [Board Name] affiliated
    - Secondary Section: [Board Name] affiliated
    - Senior Secondary: [Board Name] affiliated
    - Board affiliation number: [Number]
    - Regular inspection and quality audits by board officials

    **Subject Offerings**

    **Primary Classes (1-5):**
    - English Language and Literature
    - Hindi/Regional Language
    - Mathematics
    - Environmental Studies
    - General Knowledge
    - Art and Craft
    - Physical Education
    - Moral Science

    **Secondary Classes (6-8):**
    - English
    - Hindi/Regional Language
    - Mathematics
    - Science
    - Social Studies
    - Computer Science
    - Art Education
    - Physical Education

    **Classes 9-10:**
    - English Language and Literature
    - Hindi/Regional Language
    - Mathematics
    - Science (Physics, Chemistry, Biology)
    - Social Science (History, Geography, Political Science, Economics)
    - Additional subject options available

    **Classes 11-12 Streams:**
    **Science Stream:**
    - Physics, Chemistry, Mathematics
    - Physics, Chemistry, Biology
    - Optional: Computer Science, Physical Education

    **Commerce Stream:**
    - Accountancy, Business Studies, Economics
    - Optional: Mathematics, Computer Science, Physical Education

    **Humanities Stream:**
    - History, Geography, Political Science
    - Optional: Economics, Psychology, Physical Education

    **Textbooks and Learning Resources**
    - NCERT books as primary textbooks
    - Reference books recommended by subject teachers
    - Digital learning resources and educational apps
    - Library books and periodicals
    - Online learning platforms subscription

    **Assessment Guidelines**
    - Regular homework assignments
    - Project work for practical understanding
    - Field trips and educational tours
    - Science exhibitions and math olympiads
    - Language competitions and debates

    **Special Programs**
    - Remedial classes for slow learners
    - Advanced learning programs for gifted students
    - Career guidance and counseling
    - Personality development sessions
    - Life skills education

    ## Chapter 6: Facilities and Infrastructure

    **Academic Facilities**

    **Classrooms:**
    - Smart classrooms with projectors and audio systems
    - Air-conditioned rooms for senior classes
    - Flexible seating arrangements for group activities
    - Natural lighting and proper ventilation
    - Safety measures including fire extinguishers

    **Laboratories:**
    - **Physics Lab**: Modern equipment for class 9-12 experiments
    - **Chemistry Lab**: Safety equipment and fume hoods
    - **Biology Lab**: Microscopes, specimens, and models
    - **Computer Lab**: Latest computers with internet connectivity
    - **Language Lab**: Audio-visual aids for language learning
    - **Mathematics Lab**: Manipulatives and geometric instruments

    **Library Services:**
    - Central library with 10,000+ books
    - Reference section with encyclopedias and dictionaries
    - Digital library with e-books and online resources
    - Newspaper and magazine section
    - Reading room with comfortable seating
    - Library periods for all classes
    - Book borrowing facility for students and staff

    **Sports and Recreation**

    **Outdoor Facilities:**
    - Football and cricket ground
    - Basketball and volleyball courts
    - Athletic track for running events
    - Play area for junior students
    - Outdoor fitness equipment

    **Indoor Facilities:**
    - Badminton court
    - Table tennis room
    - Chess and carrom room
    - Gymnasium with modern equipment
    - Yoga and meditation hall

    **Health and Safety**

    **Medical Facilities:**
    - Full-time qualified nurse on campus
    - First aid room equipped with basic medical supplies
    - Tie-up with nearby hospital for emergencies
    - Annual health checkups by visiting doctors
    - Vaccination programs as per health department guidelines

    **Safety Measures:**
    - 24/7 security guards at all entry points
    - CCTV cameras in common areas
    - Fire safety equipment in all buildings
    - Emergency evacuation procedures
    - Visitor management system with ID verification

    **Transportation Services**
    - GPS-enabled school buses covering major residential areas
    - Trained drivers with clean driving records
    - Female attendant in buses with girl students
    - First aid kit and emergency contact numbers in each bus
    - Real-time tracking system for parents
    - Regular vehicle maintenance and safety checks

    **Cafeteria and Nutrition**
    - Hygienic kitchen with quality food preparation
    - Nutritious meal options for different age groups
    - Special dietary accommodations for health conditions
    - Mid-day meal program for eligible students
    - Safe drinking water through RO systems
    - Regular health department inspections

    **Technology Integration**
    - High-speed internet connectivity throughout campus
    - Student information management system
    - Parent communication app for updates and announcements
    - Online assignment submission portal
    - Digital attendance system
    - Virtual classroom facility for distance learning

    ## Chapter 7: Rules and Regulations

    **General Discipline**

    **Attendance Requirements:**
    - Minimum 75% attendance required for appearing in examinations
    - Medical certificates required for absence beyond 3 consecutive days
    - Prior permission needed for planned leaves
    - Repeated unexplained absences may result in disciplinary action

    **Uniform Policy:**
    - School uniform mandatory on all working days
    - PE uniform required for sports periods
    - Proper grooming and hygiene expected
    - Hair should be neatly tied (for girls) and trimmed (for boys)
    - Minimal jewelry allowed, no expensive items

    **Code of Conduct:**
    - Respectful behavior toward teachers, staff, and fellow students
    - Use of appropriate language at all times
    - Prohibition of bullying or harassment in any form
    - No bringing of prohibited items (mobile phones, electronic games, etc.)
    - Responsibility for personal belongings

    **Academic Integrity:**
    - Original work expected in all assignments and projects
    - No copying or plagiarism in examinations
    - Proper citation required for research work
    - Cheating or malpractice leads to disciplinary action
    - Honor code to be signed by all students

    **Mobile Phone and Electronics Policy**
    - Mobile phones not allowed for students below class 8
    - Senior students may bring phones with written parent permission
    - Phones must be switched off during school hours
    - School not responsible for lost or damaged electronic items
    - Violation may result in confiscation and parent meeting

    **Disciplinary Measures**
    - **Level 1**: Verbal warning and counseling
    - **Level 2**: Written warning to parents
    - **Level 3**: Suspension for specified period
    - **Level 4**: Removal from school in extreme cases
    - Parent involvement required at each level

    **Library Rules**
    - Maintain silence in library premises
    - Books issued for 15 days, renewable once
    - Fine for late return: ₹2 per day per book
    - Replacement cost for lost or damaged books
    - No food or drinks allowed in library area

    **Examination Rules**
    - Reach examination hall 15 minutes before start time
    - Bring only permitted items (pen, pencil, eraser, etc.)
    - No talking or unfair means during examination
    - Follow seating arrangement as per hall ticket
    - Submit answer sheet before leaving the hall

    ## Chapter 8: Communication and Parent Engagement

    **Parent Communication Channels**

    **Official Communication:**
    - School website: [www.schoolname.edu.in]
    - Email: [info@schoolname.edu.in]
    - Phone: [School phone number]
    - Parent WhatsApp groups for each class
    - Monthly newsletter with school updates

    **Parent-Teacher Interaction:**
    - Scheduled monthly meetings on first Saturday
    - Individual parent conferences on appointment
    - Open door policy for urgent concerns
    - Annual parent feedback surveys
    - Parent orientation programs for new admissions

    **Digital Platforms**
    - Parent mobile app for real-time updates
    - SMS alerts for important announcements
    - Online fee payment portal
    - Digital diary for homework and assignments
    - Virtual parent-teacher meetings when needed

    **Parent Involvement Opportunities**
    - Parent-Teacher Association (PTA) membership
    - Volunteer opportunities for school events
    - Career guidance sessions by parent professionals
    - Educational tours and field trip assistance
    - School improvement committee participation

    **Complaint and Grievance Procedure**
    - **Step 1**: Discuss with class teacher
    - **Step 2**: Meet with subject coordinator
    - **Step 3**: Approach vice principal
    - **Step 4**: Final appeal to principal
    - Written complaints to be submitted within 15 days of incident

    **Emergency Communication**
    - Emergency contact numbers displayed prominently
    - Rapid communication system for school closures
    - Parent emergency contact database updated annually
    - Crisis communication plan for natural disasters
    - Medical emergency contact protocol

    ## Chapter 9: Special Programs and Activities

    **Co-curricular Activities**

    **Sports Programs:**
    - Inter-house competitions throughout the year
    - District and state level participation
    - Annual sports day with various events
    - Specialized coaching for talented students
    - Sports equipment provided by school

    **Cultural Activities:**
    - Annual day celebrations with cultural performances
    - Inter-school competitions in music, dance, drama
    - Art and craft exhibitions
    - Literary competitions (essay, poetry, debate)
    - Cultural exchange programs with other schools

    **Academic Competitions:**
    - Science exhibitions and model making
    - Mathematics olympiad preparation
    - Quiz competitions on various subjects
    - Spelling bee and vocabulary contests
    - Environmental awareness programs

    **Special Interest Clubs**
    - **Science Club**: Experiments and science projects
    - **Literary Club**: Reading, writing, and book discussions
    - **Environmental Club**: Green initiatives and awareness
    - **Computer Club**: Advanced programming and robotics
    - **Music Club**: Vocal and instrumental training
    - **Art Club**: Drawing, painting, and craft activities

    **Career Guidance Programs**
    - Career counseling sessions for senior students
    - Aptitude tests to identify strengths and interests
    - Guest lectures by professionals from various fields
    - College and university visit programs
    - Scholarship guidance for higher education

    **Life Skills Education**
    - Personality development workshops
    - Public speaking and presentation skills
    - Time management and study skills
    - Financial literacy programs
    - Health and wellness education

    ## Chapter 10: Health and Wellness

    **Health Services**

    **Medical Care:**
    - Qualified nurse available during school hours
    - Basic medical supplies and first aid equipment
    - Tie-up with nearby hospitals for emergencies
    - Regular health checkups by visiting doctors
    - Maintenance of individual health records

    **Mental Health and Counseling**
    - Trained counselors available for student support
    - Stress management workshops during exam periods
    - Anti-bullying programs and peer mediation
    - Support for students with learning difficulties
    - Parent counseling for family-related issues

    **Hygiene and Sanitation**
    - Clean and well-maintained washrooms
    - Regular sanitization of classrooms and common areas
    - Hand wash stations at multiple locations
    - Safe drinking water through tested RO systems
    - Waste segregation and proper disposal methods
    
    **Special Needs Support**
    - Individualized education plans for students with disabilities
    - Barrier-free infrastructure for physically challenged students
    - Special educators and support staff
    - Assistive technology and learning aids
    - Inclusive classroom practices

    **Emergency Procedures**
    - First aid training for staff members
    - Emergency contact database for all students
    - Evacuation procedures for fire and natural disasters
    - Ambulance service tie-up for medical emergencies
    - Crisis management team for handling emergencies

    Remember: This institution is committed to providing a safe, nurturing, and enriching environment for all students. For any specific questions not covered in this guide, please contact the school office directly.
    """

    def search_content(self, query: str, content_type: str = "all") -> Dict:
        """Search across all content for relevant information"""
        try:
            results = {}

            if content_type in ["all", "subjects"]:
                for subject in self.subjects:
                    content = self.load_subject_content(subject)
                    relevant = self.find_relevant_content(query, content, 4)
                    if relevant and len(relevant.strip()) > 50:
                        results[subject] = {
                            "type": "subject",
                            "content": relevant,
                            "name": self.subjects[subject]["name"],
                        }

            if content_type in ["all", "institutional"]:
                content = self.load_institutional_content()
                relevant = self.find_relevant_content(query, content, 5)
                if relevant and len(relevant.strip()) > 50:
                    results["institutional"] = {
                        "type": "institutional",
                        "content": relevant,
                        "name": "Institutional FAQ",
                    }

            return results

        except Exception as e:
            print(f"❌ Error searching content: {e}")
            return {}

    def get_content_stats(self) -> Dict:
        """Get statistics about content availability"""
        stats = {
            "subjects_available": 0,
            "subjects_with_content": 0,
            "institutional_available": False,
            "total_content_size": 0,
        }

        try:
            stats["subjects_available"] = len(self.subjects)

            for subject in self.subjects:
                content = self.load_subject_content(subject)
                if content and len(content.strip()) > 100:
                    stats["subjects_with_content"] += 1
                    stats["total_content_size"] += len(content)

            institutional_content = self.load_institutional_content()
            if institutional_content and len(institutional_content.strip()) > 100:
                stats["institutional_available"] = True
                stats["total_content_size"] += len(institutional_content)

        except Exception as e:
            print(f"❌ Error getting content stats: {e}")

        return stats
