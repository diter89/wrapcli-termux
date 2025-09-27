#!/usr/bin/env python3

def main():
    try:
        from . import app
        
        if hasattr(app, 'main'):
            app.main()
        else:
            print("Error: No main() function found in app.py")
            return 1
            
    except KeyboardInterrupt:
        print("\nBye!")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
