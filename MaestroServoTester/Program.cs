using Spectre.Console;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace MaestroServoTester;

class Program
{
    static void Main(string[] args)
    {
        // Parse command line arguments
        bool mockMode = args.Contains("--mock") || args.Contains("-m");
        string? configPath = GetConfigPath(args);
        int? testChannel = GetChannelArg(args);
        int? testLeg = GetLegArg(args);
        bool testAll = args.Contains("--all") || args.Contains("-a");
        bool showMap = args.Contains("--map");

        // Display banner
        DisplayBanner();

        try
        {
            // Load configuration
            var config = LoadConfiguration(configPath);

            // Create Maestro controller
            using var controller = new MaestroController(
                config.Servos.Driver.Serial_Port,
                config.Servos.Driver.Baud_Rate,
                config.Servos.Specs.Min_Pulse,
                config.Servos.Specs.Max_Pulse,
                mockMode
            );

            // Open connection
            controller.Open();

            // Create tester
            var tester = new ServoTester(controller, config.Servos.Channels);

            // Handle command-line operations
            if (showMap)
            {
                tester.PrintChannelMap();
                return;
            }

            if (testChannel.HasValue)
            {
                tester.PrintChannelMap();
                tester.TestChannel(testChannel.Value);
                return;
            }

            if (testLeg.HasValue)
            {
                tester.PrintChannelMap();
                tester.TestLeg(testLeg.Value);
                return;
            }

            if (testAll)
            {
                tester.PrintChannelMap();
                tester.TestAllServos();
                return;
            }

            // Interactive mode
            RunInteractiveMode(tester);
        }
        catch (Exception ex)
        {
            AnsiConsole.MarkupLine($"[red]✗ Error: {ex.Message}[/]");
            Environment.Exit(1);
        }
    }

    static void DisplayBanner()
    {
        AnsiConsole.Write(
            new FigletText("Maestro Servo Tester")
                .LeftJustified()
                .Color(Color.Cyan1));

        AnsiConsole.MarkupLine("[dim]Pololu Maestro Servo Wiring Test Utility - C# .NET 9[/]");
        AnsiConsole.WriteLine();
    }

    static HardwareConfig LoadConfiguration(string? configPath)
    {
        // Default path relative to executable
        configPath ??= Path.Combine("..", "hexapod_control", "config", "hardware.yaml");

        if (!File.Exists(configPath))
        {
            // Try alternative path
            configPath = Path.Combine("..", "..", "hexapod_control", "config", "hardware.yaml");
        }

        if (!File.Exists(configPath))
        {
            throw new FileNotFoundException($"Configuration file not found: {configPath}");
        }

        AnsiConsole.MarkupLine($"[dim]Loading configuration from: {configPath}[/]");

        var deserializer = new DeserializerBuilder()
            .WithNamingConvention(UnderscoredNamingConvention.Instance)
            .Build();

        var yaml = File.ReadAllText(configPath);
        var config = deserializer.Deserialize<HardwareConfig>(yaml);

        AnsiConsole.MarkupLine($"[green]✓ Configuration loaded[/]");
        AnsiConsole.MarkupLine($"[dim]  Port: {config.Servos.Driver.Serial_Port} @ {config.Servos.Driver.Baud_Rate} baud[/]");
        AnsiConsole.WriteLine();

        return config;
    }

    static void RunInteractiveMode(ServoTester tester)
    {
        AnsiConsole.MarkupLine("[bold yellow]═══════════════════════════════════════════════════[/]");
        AnsiConsole.MarkupLine("[bold yellow]        INTERACTIVE SERVO WIRING TEST             [/]");
        AnsiConsole.MarkupLine("[bold yellow]═══════════════════════════════════════════════════[/]");
        AnsiConsole.WriteLine();

        PrintHelp();
        tester.PrintChannelMap();
        AnsiConsole.WriteLine();

        while (true)
        {
            var input = AnsiConsole.Ask<string>("[cyan]Enter command:[/]").Trim().ToLower();

            if (string.IsNullOrEmpty(input))
                continue;

            try
            {
                switch (input)
                {
                    case "quit" or "exit" or "q":
                        AnsiConsole.MarkupLine("[yellow]Exiting...[/]");
                        tester.MoveAllToNeutral();
                        return;

                    case "help" or "h" or "?":
                        PrintHelp();
                        break;

                    case "map" or "m":
                        tester.PrintChannelMap();
                        break;

                    case "all" or "a":
                        tester.TestAllServos();
                        break;

                    case "neutral" or "n":
                        AnsiConsole.MarkupLine("[cyan]Moving all servos to neutral position...[/]");
                        tester.MoveAllToNeutral();
                        AnsiConsole.MarkupLine("[green]✓ All servos at neutral (90°)[/]");
                        break;

                    case var s when s.StartsWith("leg "):
                        if (int.TryParse(s.Substring(4).Trim(), out int leg) && leg >= 0 && leg <= 5)
                        {
                            tester.TestLeg(leg);
                        }
                        else
                        {
                            AnsiConsole.MarkupLine("[red]Invalid leg number. Use: leg 0-5[/]");
                        }
                        break;

                    case var s when int.TryParse(s, out int channel) && channel >= 0 && channel <= 17:
                        tester.TestChannel(channel);
                        break;

                    default:
                        AnsiConsole.MarkupLine($"[red]Unknown command: {input}. Type 'help' for commands.[/]");
                        break;
                }
            }
            catch (Exception ex)
            {
                AnsiConsole.MarkupLine($"[red]✗ Error: {ex.Message}[/]");
            }

            AnsiConsole.WriteLine();
        }
    }

    static void PrintHelp()
    {
        var table = new Table()
            .Border(TableBorder.Rounded)
            .Title("[bold yellow]COMMANDS[/]");

        table.AddColumn("[bold]Command[/]");
        table.AddColumn("[bold]Description[/]");

        table.AddRow("0-17", "Test specific channel number");
        table.AddRow("leg <0-5>", "Test all servos on leg");
        table.AddRow("all", "Test all servos sequentially");
        table.AddRow("map", "Show channel mapping table");
        table.AddRow("neutral", "Move all servos to 90°");
        table.AddRow("help", "Show this help");
        table.AddRow("quit", "Exit program");

        AnsiConsole.Write(table);
        AnsiConsole.WriteLine();

        var legTable = new Table()
            .Border(TableBorder.Rounded)
            .Title("[bold cyan]LEG NUMBERING[/]");

        legTable.AddColumn("[bold]Leg[/]");
        legTable.AddColumn("[bold]Position[/]");

        legTable.AddRow("0", "Front Right");
        legTable.AddRow("1", "Middle Right");
        legTable.AddRow("2", "Rear Right");
        legTable.AddRow("3", "Rear Left");
        legTable.AddRow("4", "Middle Left");
        legTable.AddRow("5", "Front Left");

        AnsiConsole.Write(legTable);
        AnsiConsole.WriteLine();
    }

    static string? GetConfigPath(string[] args)
    {
        int configIdx = Array.IndexOf(args, "--config");
        if (configIdx >= 0 && configIdx + 1 < args.Length)
            return args[configIdx + 1];

        configIdx = Array.IndexOf(args, "-c");
        if (configIdx >= 0 && configIdx + 1 < args.Length)
            return args[configIdx + 1];

        return null;
    }

    static int? GetChannelArg(string[] args)
    {
        int idx = Array.IndexOf(args, "--channel");
        if (idx >= 0 && idx + 1 < args.Length && int.TryParse(args[idx + 1], out int ch))
            return ch;

        idx = Array.IndexOf(args, "-ch");
        if (idx >= 0 && idx + 1 < args.Length && int.TryParse(args[idx + 1], out ch))
            return ch;

        return null;
    }

    static int? GetLegArg(string[] args)
    {
        int idx = Array.IndexOf(args, "--leg");
        if (idx >= 0 && idx + 1 < args.Length && int.TryParse(args[idx + 1], out int leg))
            return leg;

        idx = Array.IndexOf(args, "-l");
        if (idx >= 0 && idx + 1 < args.Length && int.TryParse(args[idx + 1], out leg))
            return leg;

        return null;
    }
}
