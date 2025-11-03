using System.IO.Ports;

namespace MaestroServoTester;

/// <summary>
/// Controls Pololu Maestro servo controller via USB serial connection
/// Uses Compact Protocol (no device number)
/// </summary>
public class MaestroController : IDisposable
{
    private readonly SerialPort _serialPort;
    private readonly int _minPulse;
    private readonly int _maxPulse;
    private readonly bool _mockMode;

    public MaestroController(string portName, int baudRate, int minPulse, int maxPulse, bool mockMode = false)
    {
        _minPulse = minPulse;
        _maxPulse = maxPulse;
        _mockMode = mockMode;

        if (!mockMode)
        {
            _serialPort = new SerialPort(portName, baudRate)
            {
                DataBits = 8,
                Parity = Parity.None,
                StopBits = StopBits.One,
                Handshake = Handshake.None,
                WriteTimeout = 1000,
                ReadTimeout = 1000
            };
        }
        else
        {
            _serialPort = null!; // Mock mode - no actual port
        }
    }

    public void Open()
    {
        if (_mockMode)
        {
            Console.WriteLine("[MOCK] Maestro controller opened in mock mode");
            return;
        }

        try
        {
            _serialPort.Open();
            Console.WriteLine($"✓ Maestro connected on {_serialPort.PortName}");
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException($"Failed to open serial port: {ex.Message}", ex);
        }
    }

    public void Close()
    {
        if (_mockMode) return;

        if (_serialPort?.IsOpen == true)
        {
            _serialPort.Close();
            Console.WriteLine("✓ Maestro disconnected");
        }
    }

    /// <summary>
    /// Set servo target position using Compact Protocol
    /// Format: [0x84][channel][target_low][target_high]
    /// </summary>
    public bool SetTarget(int channel, int target)
    {
        if (channel < 0 || channel > 17)
        {
            Console.WriteLine($"✗ Invalid channel: {channel}");
            return false;
        }

        // Clamp target to valid range
        target = Math.Clamp(target, 0, 65535);

        // Build command using Compact Protocol (no device number)
        byte[] command = new byte[]
        {
            0x84,                        // Set Target command
            (byte)channel,               // Channel (0-17)
            (byte)(target & 0x7F),      // Low 7 bits
            (byte)((target >> 7) & 0x7F) // High 7 bits
        };

        if (_mockMode)
        {
            Console.WriteLine($"[MOCK] Set channel {channel} to target {target} (0x{target:X4})");
            return true;
        }

        try
        {
            _serialPort.Write(command, 0, command.Length);
            return true;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"✗ Failed to send command: {ex.Message}");
            return false;
        }
    }

    /// <summary>
    /// Set servo angle (0-180 degrees)
    /// </summary>
    public bool SetAngle(int channel, double angle)
    {
        // Clamp angle
        angle = Math.Clamp(angle, 0, 180);

        // Convert angle to target (quarter-microseconds)
        double pulseRange = _maxPulse - _minPulse;
        int target = (int)(_minPulse + (angle / 180.0) * pulseRange);

        return SetTarget(channel, target);
    }

    /// <summary>
    /// Move servo to neutral position (90 degrees)
    /// </summary>
    public bool MoveToNeutral(int channel)
    {
        return SetAngle(channel, 90);
    }

    /// <summary>
    /// Disable servo (set target to 0)
    /// </summary>
    public bool DisableServo(int channel)
    {
        if (_mockMode)
        {
            Console.WriteLine($"[MOCK] Disable channel {channel}");
            return true;
        }

        byte[] command = new byte[] { 0x84, (byte)channel, 0, 0 };

        try
        {
            _serialPort.Write(command, 0, command.Length);
            return true;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"✗ Failed to disable servo: {ex.Message}");
            return false;
        }
    }

    public void Dispose()
    {
        Close();
        _serialPort?.Dispose();
    }
}
