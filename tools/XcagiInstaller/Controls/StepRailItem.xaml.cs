using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;

namespace XcagiInstaller.Controls;

public partial class StepRailItem : System.Windows.Controls.UserControl
{
    public static readonly DependencyProperty LabelProperty =
        DependencyProperty.Register(nameof(Label), typeof(string), typeof(StepRailItem),
            new PropertyMetadata("步骤", OnLabelChanged));

    public static readonly DependencyProperty StepIndexProperty =
        DependencyProperty.Register(nameof(StepIndex), typeof(int), typeof(StepRailItem),
            new PropertyMetadata(1, OnRailChanged));

    public static readonly DependencyProperty IsFirstProperty =
        DependencyProperty.Register(nameof(IsFirst), typeof(bool), typeof(StepRailItem),
            new PropertyMetadata(false, OnRailChanged));

    public static readonly DependencyProperty IsLastProperty =
        DependencyProperty.Register(nameof(IsLast), typeof(bool), typeof(StepRailItem),
            new PropertyMetadata(false, OnRailChanged));

    public static readonly DependencyProperty IsCurrentProperty =
        DependencyProperty.Register(nameof(IsCurrent), typeof(bool), typeof(StepRailItem),
            new PropertyMetadata(false, OnRailChanged));

    public static readonly DependencyProperty IsCompletedProperty =
        DependencyProperty.Register(nameof(IsCompleted), typeof(bool), typeof(StepRailItem),
            new PropertyMetadata(false, OnRailChanged));

    public string Label
    {
        get => (string)GetValue(LabelProperty);
        set => SetValue(LabelProperty, value);
    }

    public int StepIndex
    {
        get => (int)GetValue(StepIndexProperty);
        set => SetValue(StepIndexProperty, value);
    }

    public bool IsFirst
    {
        get => (bool)GetValue(IsFirstProperty);
        set => SetValue(IsFirstProperty, value);
    }

    public bool IsLast
    {
        get => (bool)GetValue(IsLastProperty);
        set => SetValue(IsLastProperty, value);
    }

    public bool IsCurrent
    {
        get => (bool)GetValue(IsCurrentProperty);
        set => SetValue(IsCurrentProperty, value);
    }

    public bool IsCompleted
    {
        get => (bool)GetValue(IsCompletedProperty);
        set => SetValue(IsCompletedProperty, value);
    }

    public StepRailItem()
    {
        InitializeComponent();
        Loaded += (_, _) => ApplyVisual();
    }

    private static void OnLabelChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
        if (d is StepRailItem item)
            item.StepLabel.Text = e.NewValue as string ?? "";
    }

    private static void OnRailChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
        if (d is StepRailItem item)
            item.ApplyVisual();
    }

    private void ApplyVisual()
    {
        StepLabel.Text = Label;
        StepNumber.Text = StepIndex.ToString();
        ConnectorTop.Visibility = IsFirst ? Visibility.Collapsed : Visibility.Visible;
        ConnectorBottom.Visibility = IsLast ? Visibility.Collapsed : Visibility.Visible;

        if (IsCurrent)
        {
            StepBadge.Background = System.Windows.Media.Brushes.White;
            StepBadge.BorderBrush = System.Windows.Media.Brushes.White;
            StepNumber.Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(22, 119, 255));
            StepLabel.Foreground = System.Windows.Media.Brushes.White;
            StepLabel.FontWeight = FontWeights.SemiBold;
        }
        else if (IsCompleted)
        {
            StepBadge.Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(200, 255, 255, 255));
            StepBadge.BorderBrush = System.Windows.Media.Brushes.Transparent;
            StepNumber.Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(22, 119, 255));
            StepLabel.Foreground = new SolidColorBrush(System.Windows.Media.Color.FromArgb(230, 255, 255, 255));
            StepLabel.FontWeight = FontWeights.Normal;
        }
        else
        {
            StepBadge.Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(51, 255, 255, 255));
            StepBadge.BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromArgb(136, 255, 255, 255));
            StepNumber.Foreground = System.Windows.Media.Brushes.White;
            StepLabel.Foreground = new SolidColorBrush(System.Windows.Media.Color.FromArgb(153, 255, 255, 255));
            StepLabel.FontWeight = FontWeights.Normal;
        }
    }
}
