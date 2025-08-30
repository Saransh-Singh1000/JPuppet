import time
from JPuppet import JPuppet

# Initialize JPuppet HotSpot-style
puppet = JPuppet()

# Sample Java code to test
java_code = """
public class AddTwo {
    public static void main(String[] args) {
        int result = 2 + 2;
        System.out.println(result);
    }
}
"""

# Run it multiple times to see HotSpot JIT effect
for i in range(4):
    start = time.time()
    output = puppet.Run(java_code)
    elapsed = time.time() - start
    print(f"Run {i+1}: Output={output}, Time={elapsed:.6f}s")
